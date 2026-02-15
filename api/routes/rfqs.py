"""
RFQ Routes - Lead Scoring API Endpoints
"""
from flask import Blueprint, jsonify, request
import psycopg2
import psycopg2.extras
from psycopg2 import Error
from config import Config

rfqs_bp = Blueprint('rfqs', __name__)


def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = psycopg2.connect(**Config.get_db_config())
        return connection
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None


@rfqs_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    GET /api/health
    """
    try:
        conn = get_db_connection()
        if conn.closed == 0:
            conn.close()
            return jsonify({
                'status': 'healthy',
                'database': 'connected'
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected'
            }), 503
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@rfqs_bp.route('/rfqs/scored', methods=['GET'])
def get_scored_rfqs():
    """
    Get all RFQs with lead scores, sorted by score (highest first)
    
    GET /api/rfqs/scored
    
    Optional Query Parameters:
    - limit: Number of results (default: 50, max: 100)
    - min_score: Minimum lead score filter (0-100)
    - rfqscore: Filter by buyer rfqscore (1-5)
    - status: Filter by RFQ status (published, closed, etc.)
    
    Returns:
    {
        "success": true,
        "count": 10,
        "rfqs": [...]
    }
    """
    
    # Get query parameters
    limit = request.args.get('limit', default=50, type=int)
    min_score = request.args.get('min_score', default=0, type=int)
    rfqscore_filter = request.args.get('rfqscore', default=None, type=int)
    status_filter = request.args.get('status', default='published', type=str)
    
    # Validate and cap limit
    limit = min(limit, 100)
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Build dynamic query
        query = """
            SELECT 
                r.rfq_id,
                r.title,
                r.description,
                r.category,
                r.budget_min,
                r.budget_max,
                r.created_at,
                
                -- Buyer information
                b.business_name AS buyer_name,
                b.brank AS buyer_brank,
                b.primary_category AS buyer_category,
                b.business_id AS buyer_id,
                
                -- Lead score information
                s.lead_score,
                s.conversion_probability,
                s.model_version,
                s.predicted_at,
                
                -- Priority classification
                CASE 
                    WHEN s.lead_score >= 70 THEN 'High'
                    WHEN s.lead_score >= 40 THEN 'Medium'
                    ELSE 'Low'
                END AS priority,
                
                -- Score color (for UI badges)
                CASE 
                    WHEN s.lead_score >= 70 THEN 'green'
                    WHEN s.lead_score >= 40 THEN 'yellow'
                    ELSE 'gray'
                END AS score_color
                
            FROM rfqs r
            JOIN businesses b ON r.buyer_business_id = b.business_id
            JOIN rfq_lead_scores s ON r.rfq_id = s.rfq_id
            
            WHERE r.status = %s
              AND s.lead_score >= %s
        """
        
        params = [status_filter, min_score]
        
        # Add rfqscore filter if provided
        if rfqscore_filter:
            query += " AND b.brank = %s"
            params.append(rfqscore_filter)
        
        # Sort and limit
        query += """
            ORDER BY s.lead_score DESC, r.created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert DictRow to dict so JSON has proper keys (UI expects e.g. r.rfq_id, r.lead_score)
        rfqs = [dict(r) for r in rows]

        return jsonify({
            'success': True,
            'count': len(rfqs),
            'filters': {
                'status': status_filter,
                'min_score': min_score,
                'rfqscore': rfqscore_filter,
                'limit': limit
            },
            'rfqs': rfqs
        }), 200
        
    except Error as e:
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@rfqs_bp.route('/rfqs/<rfq_id>/score', methods=['GET'])
def get_rfq_score(rfq_id):
    """
    Get lead score for a specific RFQ
    
    GET /api/rfqs/<rfq_id>/score
    
    Returns:
    {
        "success": true,
        "rfq": {...}
    }
    """
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        query = """
            SELECT 
                r.rfq_id,
                r.title,
                r.description,
                r.category,
                r.budget_min,
                r.budget_max,
                r.created_at,
                r.status,
                
                -- Buyer information
                b.business_name AS buyer_name,
                b.brank AS buyer_brank,
                b.primary_category AS buyer_category,
                
                -- Lead score information
                s.lead_score,
                s.conversion_probability,
                s.model_version,
                s.predicted_at,
                
                -- Priority
                CASE 
                    WHEN s.lead_score >= 70 THEN 'High'
                    WHEN s.lead_score >= 40 THEN 'Medium'
                    ELSE 'Low'
                END AS priority
                
            FROM rfqs r
            JOIN businesses b ON r.buyer_business_id = b.business_id
            LEFT JOIN rfq_lead_scores s ON r.rfq_id = s.rfq_id
            
            WHERE r.rfq_id = %s
        """
        
        cursor.execute(query, (rfq_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        rfq = dict(row) if row else None
        if not rfq:
            return jsonify({
                'success': False,
                'error': 'RFQ not found'
            }), 404
        
        if not rfq['lead_score']:
            return jsonify({
                'success': False,
                'error': 'RFQ not yet scored',
                'rfq_id': rfq_id
            }), 404
        
        return jsonify({
            'success': True,
            'rfq': rfq
        }), 200
        
    except Error as e:
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@rfqs_bp.route('/rfqs/stats', methods=['GET'])
def get_rfq_stats():
    """
    Get statistics about RFQ lead scores
    
    GET /api/rfqs/stats
    
    Returns:
    {
        "success": true,
        "stats": {
            "total_scored": 100,
            "high_priority": 25,
            "medium_priority": 40,
            "low_priority": 35,
            "avg_score": 52.3,
            ...
        }
    }
    """
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        query = """
            SELECT 
                COUNT(*) AS total_scored,
                
                -- Priority distribution
                SUM(CASE WHEN s.lead_score >= 70 THEN 1 ELSE 0 END) AS high_priority,
                SUM(CASE WHEN s.lead_score >= 40 AND s.lead_score < 70 THEN 1 ELSE 0 END) AS medium_priority,
                SUM(CASE WHEN s.lead_score < 40 THEN 1 ELSE 0 END) AS low_priority,
                
                -- Score statistics
                ROUND(AVG(s.lead_score), 1) AS avg_score,
                MIN(s.lead_score) AS min_score,
                MAX(s.lead_score) AS max_score,
                
                -- Conversion probability statistics
                ROUND(AVG(s.conversion_probability), 3) AS avg_conversion_prob,
                
                -- rfqscore distribution
                SUM(CASE WHEN b.brank = 1 THEN 1 ELSE 0 END) AS ss1_count,
                SUM(CASE WHEN b.brank = 2 THEN 1 ELSE 0 END) AS ss2_count,
                SUM(CASE WHEN b.brank = 3 THEN 1 ELSE 0 END) AS ss3_count,
                SUM(CASE WHEN b.brank = 4 THEN 1 ELSE 0 END) AS ss4_count,
                SUM(CASE WHEN b.brank = 5 THEN 1 ELSE 0 END) AS ss5_count
                
            FROM rfqs r
            JOIN businesses b ON r.buyer_business_id = b.business_id
            JOIN rfq_lead_scores s ON r.rfq_id = s.rfq_id
            WHERE r.status = 'published'
        """
        
        cursor.execute(query)
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        stats = dict(row) if row else None
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Error as e:
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@rfqs_bp.route('/rfqs/score-distribution', methods=['GET'])
def get_score_distribution():
    """
    Get distribution of lead scores in buckets
    
    GET /api/rfqs/score-distribution
    
    Returns:
    {
        "success": true,
        "distribution": [
            {"range": "0-20", "count": 15},
            {"range": "20-40", "count": 25},
            ...
        ]
    }
    """
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({
                'success': False,
                'error': 'Database connection failed'
            }), 500
        
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        query = """
            SELECT 
                CASE 
                    WHEN s.lead_score >= 80 THEN '80-100'
                    WHEN s.lead_score >= 60 THEN '60-79'
                    WHEN s.lead_score >= 40 THEN '40-59'
                    WHEN s.lead_score >= 20 THEN '20-39'
                    ELSE '0-19'
                END AS score_range,
                COUNT(*) AS count,
                ROUND(AVG(s.conversion_probability), 3) AS avg_conversion_prob
            FROM rfqs r
            JOIN rfq_lead_scores s ON r.rfq_id = s.rfq_id
            WHERE r.status = 'published'
            GROUP BY score_range
            ORDER BY MIN(s.lead_score) DESC
        """
        
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        distribution = [dict(r) for r in rows]
        return jsonify({
            'success': True,
            'distribution': distribution
        }), 200
        
    except Error as e:
        return jsonify({
            'success': False,
            'error': f'Database error: {str(e)}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500