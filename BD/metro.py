## =============================================
## ============== Bases de Dados ===============
## ============== LEI  2025/2026 ===============
## =============================================

import flask
from flask import request, jsonify
import logging
import psycopg2
import jwt
import datetime
import hashlib
from functools import wraps

app = flask.Flask(__name__)

# Chave secreta para assinar os tokens JWT
app.config['SECRET_KEY'] = 'chave_secreta_super_segura_bd_2025'

StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500
}

##########################################################
## DATABASE ACCESS
##########################################################

def db_connection():
    # Ajusta com a tua password do Postgres local
    db = psycopg2.connect(
        user='metro', 
        password='password',
        host='127.0.0.1',
        port='5432',
        database='metro'
    )
    return db

##########################################################
## AUTHORIZATION DECORATOR
##########################################################

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
            else:
                token = auth_header
        
        if not token:
            response = {'status': StatusCodes['api_error'], 'errors': 'Token is missing!'}
            return jsonify(response), 400

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user'] #agora este user é um dicionário {id, username, role}
        except jwt.ExpiredSignatureError:
            response = {'status': StatusCodes['api_error'], 'errors': 'Token has expired!'}
            return jsonify(response), 400
        except jwt.InvalidTokenError:
            response = {'status': StatusCodes['api_error'], 'errors': 'Token is invalid!'}
            return jsonify(response), 400

        return f(current_user, *args, **kwargs)
    return decorated

##########################################################
## ENDPOINTS
##########################################################

@app.route('/')
def landing_page():
    return "API do Metro Mondego - Meta Final"


## =======================================================
## 1. USER AUTHENTICATION / LOGIN
## =======================================================
@app.route('/dbproj/user', methods=['PUT'])
def login():
    logger.info('PUT /dbproj/user (Login)')
    payload = request.get_json()

    if not payload or 'username' not in payload or 'password' not in payload:
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Missing username or password'}), 400

    username = payload['username']
    password_hash = hashlib.sha256(payload['password'].encode()).hexdigest()

    conn = db_connection()
    cur = conn.cursor()

    try:
        #descobre quem é o utilizador e o seu papel usando left joins
        query = """
            SELECT u.id, u.username, 
                   CASE 
                       WHEN sa.id IS NOT NULL THEN 'super_admin'
                       WHEN a.id IS NOT NULL THEN 'admin'
                       WHEN c.id IS NOT NULL THEN 'cliente'
                       ELSE 'unknown'
                   END as role
            FROM utilizador u
            LEFT JOIN super_admin sa ON u.id = sa.id
            LEFT JOIN administrador a ON u.id = a.id
            LEFT JOIN cliente c ON u.id = c.id
            WHERE (u.username = %s OR u.email = %s) AND u.password = %s
        """
        cur.execute(query, (username, username, password_hash))
        user_data = cur.fetchone()

        if user_data:
            user_dict = {'id': user_data[0], 'username': user_data[1], 'role': user_data[2]}
            logger.debug(f'Login successful for user: {user_dict["username"]} ({user_dict["role"]})')
            
            token = jwt.encode({
                'user': user_dict, 
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            
            response = {'status': StatusCodes['success'], 'results': token}
        else:
            response = {'status': StatusCodes['api_error'], 'errors': 'Invalid credentials'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'PUT /dbproj/user - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


## =======================================================
## 2. ADD ADMINISTRATOR
## =======================================================
@app.route('/dbproj/register/admin', methods=['PUT'])
@token_required
def add_admin(current_user):
    logger.info('PUT /dbproj/register/admin')

    #apenas super administradores podem criar outros admins
    if current_user['role'] != 'super_admin':
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Forbidden: Super Admin only'}), 403
        
    payload = request.get_json()
    if not payload or not all(k in payload for k in ("email", "name", "password")):
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Missing fields'}), 400

    email = payload['email']
    nome = payload['name']
    password_hash = hashlib.sha256(payload['password'].encode()).hexdigest()

    conn = db_connection()
    cur = conn.cursor()

    try:
        #transação: criar utilizador e depois administrador
        cur.execute("""
            INSERT INTO utilizador (username, email, password, nome) 
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (email, email, password_hash, nome)) #usamos email como username por omissão
        
        new_user_id = cur.fetchone()[0]
        
        cur.execute("INSERT INTO administrador (id) VALUES (%s)", (new_user_id,))
        
        conn.commit() #efetua o commit da transação
        response = {'status': StatusCodes['success'], 'results': {'user_id': new_user_id}}

    except psycopg2.IntegrityError as e:
        conn.rollback()
        logger.error(f'Add Admin Integrity Error: {e}')
        response = {'status': StatusCodes['api_error'], 'errors': 'Email or username already exists'}
    except Exception as error:
        conn.rollback()
        logger.error(f'Add Admin Error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


## =======================================================
## 3. ADD CUSTOMER
## =======================================================
@app.route('/dbproj/register/customer', methods=['POST'])
@token_required
def add_customer(current_user):
    logger.info('POST /dbproj/register/customer')
    
    #apenas admins (ou super admins) podem criar clientes via esta rota
    if current_user['role'] not in ['admin', 'super_admin']:
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Forbidden'}), 403

    payload = request.get_json()
    required_fields = ["name", "nif", "phone", "email", "password"]
    if not payload or not all(k in payload for k in required_fields):
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Missing fields'}), 400

    password_hash = hashlib.sha256(payload['password'].encode()).hexdigest()

    conn = db_connection()
    cur = conn.cursor()

    try:
        #transação: criar utilizador e depois cliente
        cur.execute("""
            INSERT INTO utilizador (username, email, password, nome) 
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (payload['email'], payload['email'], password_hash, payload['name']))
        
        new_user_id = cur.fetchone()[0]
        
        cur.execute("""
            INSERT INTO cliente (id, nif, telefone, saldo_carteira) 
            VALUES (%s, %s, %s, 0.0)
        """, (new_user_id, payload['nif'], payload['phone']))
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': {'user_id': new_user_id}}

    except psycopg2.IntegrityError as e:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': 'Email, NIF or Phone already exists'}
    except Exception as error:
        conn.rollback()
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


## =======================================================
## 4. UPDATE LINE OPERATION SETTINGS
## =======================================================
@app.route('/dbproj/line_operation/<int:line_id>', methods=['PUT'])
@token_required
def update_line_operation(current_user, line_id):
    logger.info(f'PUT /dbproj/line_operation/{line_id}')
    
    if current_user['role'] not in ['admin', 'super_admin']:
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Forbidden'}), 403

    payload = request.get_json()
    
    #lidar com a gralha no enunciado ("end time" vs "end_time")
    end_time = payload.get('end_time') or payload.get('end time')
    
    if not payload or 'start_time' not in payload or not end_time or 'frequency_minutes' not in payload or 'vehicle_capacity' not in payload:
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Missing fields'}), 400

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE linha_operacao 
            SET hora_inicio = %s, hora_fim = %s, freq_minutos = %s, capacidade_veic = %s 
            WHERE linha_id = %s
            RETURNING linha_id
        """, (payload['start_time'], end_time, payload['frequency_minutes'], payload['vehicle_capacity'], line_id))
        
        updated = cur.fetchone()
        if updated:
            conn.commit()
            response = {'status': StatusCodes['success'], 'errors': None}
        else:
            conn.rollback()
            response = {'status': StatusCodes['api_error'], 'errors': 'Line not found'}

    except Exception as error:
        conn.rollback()
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


## =======================================================
## 5. UPDATE FARE PRICE
## =======================================================
@app.route('/dbproj/fares/<int:fare_id>', methods=['PUT'])
@token_required
def update_fare(current_user, fare_id):
    logger.info(f'PUT /dbproj/fares/{fare_id}')
    
    if current_user['role'] not in ['admin', 'super_admin']:
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Forbidden'}), 403

    payload = request.get_json()
    if not payload or 'price' not in payload or 'effective_from' not in payload:
        return jsonify({'status': StatusCodes['api_error'], 'errors': 'Missing fields'}), 400

    conn = db_connection()
    cur = conn.cursor()

    try:
        #fechar o tarifário em vigor no dia anterior ao novo inicio_vigencia
        cur.execute("""
            UPDATE tarifario 
            SET fim_vigencia = %s::date - INTERVAL '1 day'
            WHERE tipo_produto_id = %s AND fim_vigencia IS NULL
        """, (payload['effective_from'], fare_id))
        
        #inserir o novo preço no histórico (fim_vigencia fica a NULL)
        cur.execute("""
            INSERT INTO tarifario (tipo_produto_id, preco, inicio_vigencia, fim_vigencia)
            VALUES (%s, %s, %s, NULL)
        """, (fare_id, payload['price'], payload['effective_from']))
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None}

    except psycopg2.IntegrityError:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': 'Invalid fare ID'}
    except Exception as error:
        conn.rollback()
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)



    
## =======================================================
## 6. BROADCAST NOTICE
## =======================================================
@app.route('/dbproj/notices/broadcast', methods=['POST'])
@token_required
def broadcast_notice(current_user):

    logger.info('POST /dbproj/notices/broadcast')

    if current_user['role'] not in ['admin', 'super_admin']:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Access Forbidden'
        }), 403

    payload = request.get_json()

    if not payload or 'title' not in payload or 'message' not in payload:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Missing fields'
        }), 400

    conn = db_connection()
    cur = conn.cursor()

    try:


        user_id = current_user['id']

# se for super_admin, tens de mapear para um admin real
        if current_user['role'] == 'super_admin':
            cur.execute("SELECT id FROM administrador LIMIT 1")
            user_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO aviso (
                administrador_id,
                titulo,
                mensagem
            )
            VALUES (%s, %s, %s)
        """, (
            user_id,
            payload['title'],
            payload['message']
        ))

        conn.commit()

        return {
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'title': payload['title'],
                'message': payload['message']
            }
        }

    except Exception as error:
        conn.rollback()
        return {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }

    finally:
        if conn is not None:
            conn.close()

## =======================================================
## 7. CREATE PROMOTION/ DISCOUNT RULE
## =======================================================

@app.route("/dbproj/promotions", methods=["POST"])
def create_promotion():

    data = request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            INSERT INTO promocao (
                nome,
                linha_id,
                tipo_produto_id,
                percent_desconto,
                data_inicio,
                data_fim
            )
            VALUES (%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, (
            data["name"],
            data["line_id"],
            data["product_type"],
            data["discount_percent"],
            data["start_date"],
            data["end_date"]
        ))
    
        promotion_id = cur.fetchone()[0]

        conn.commit()

        return {
            "status": 200,
            "errors": None,
            "results": {
                "promotion_id": promotion_id
            }
        }

    except Exception as e:

        conn.rollback()

        return {
            "status": 500,
            "errors": str(e)
        }

    finally:
        cur.close()
        conn.close()
        
## =======================================================
## 8. LIST LINES AND UPCOMING DEPARTURES
## =======================================================

@app.route('/dbproj/lines_next', methods=['GET'])
@token_required
def list_lines_next(current_user):

    logger.info('GET /dbproj/lines_next')

    conn = db_connection()
    cur = conn.cursor()

    try:

        query = """
            SELECT
                l.id,
                l.nome,
                v.id,
                v.direcao,
                v.data_hrpartida,
                v.capacidade_atual -
                    COUNT(val.id) AS available_capacity
            FROM linha l
            JOIN viagem v
                ON l.id = v.linha_id
            LEFT JOIN validacao val
                ON v.id = val.viagem_id
            WHERE v.data_hrpartida > NOW()
            GROUP BY
                l.id,
                l.nome,
                v.id,
                v.direcao,
                v.data_hrpartida,
                v.capacidade_atual
            ORDER BY v.data_hrpartida
            LIMIT 20
        """

        cur.execute(query)

        rows = cur.fetchall()

        results = []

        for row in rows:

            direction_parts = row[3].split('->')

            origin = direction_parts[0].strip()

            destination = ''
            if len(direction_parts) > 1:
                destination = direction_parts[1].strip()

            results.append({
                'line_id': row[0],
                'line_name': row[1],
                'origin_terminal': origin,
                'destination_terminal': destination,
                'departure_time': row[4].strftime('%Y-%m-%d %H:%M:%S'),
                'estimated_delay_min': 0,
                'available_capacity': row[5]
            })

        response = {
            'status': StatusCodes['success'],
            'errors': None,
            'results': results
        }

    except Exception as error:

        logger.error(f'GET /dbproj/lines_next error: {error}')

        response = {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }

    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)

## =======================================================
## 9. ADD WALLET FUNDS
## =======================================================
@app.route('/dbproj/wallet/topup', methods=['POST'])
@token_required
def wallet_topup(current_user):

    logger.info('POST /dbproj/wallet/topup')

    if current_user['role'] != 'cliente':
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Customers only'
        }), 403

    payload = request.get_json()

    if not payload or 'amount' not in payload:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Missing amount'
        }), 400

    conn = db_connection()
    cur = conn.cursor()

    try:

        cur.execute("""
            UPDATE cliente
            SET saldo_carteira =
                saldo_carteira + %s
            WHERE id = %s
            RETURNING saldo_carteira
        """, (
            payload['amount'],
            current_user['id']
        ))

        new_balance = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO mov_carteira (
                cliente_id,
                valor,
                tipo
            )
            VALUES (%s,%s,'topup')
        """, (
            current_user['id'],
            payload['amount']
        ))

        conn.commit()

        response = {
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'new_balance': float(new_balance)
            }
        }

    except Exception as error:

        conn.rollback()

        response = {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }

    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)

##########################################################
## HELPERS FOR FINAL ENDPOINTS
##########################################################

PRODUCT_ALIASES = {
    'single': 'single_trip',
    'single_trip': 'single_trip',
    'single trip': 'single_trip',
    'daily': 'daily',
    'day': 'daily',
    'monthly': 'monthly_pass',
    'monthly_pass': 'monthly_pass',
    'monthly pass': 'monthly_pass',
    'monthly_student': 'monthly_student_pass',
    'monthly_student_pass': 'monthly_student_pass',
    'student': 'monthly_student_pass',
    'student_monthly': 'monthly_student_pass',
    'student_monthly_pass': 'monthly_student_pass',
    'monthly_senior': 'monthly_senior_pass',
    'monthly_senior_pass': 'monthly_senior_pass',
    'senior': 'monthly_senior_pass',
    'senior_monthly': 'monthly_senior_pass',
    'senior_monthly_pass': 'monthly_senior_pass'
}


def normalize_product_type(product_type):
    product = str(product_type).strip().lower().replace('-', '_')
    product = product.replace(' ', '_')
    return PRODUCT_ALIASES.get(product, product)


def fetch_product_type(cur, product_type):
    if product_type is None:
        return None

    product = normalize_product_type(product_type)

    if isinstance(product_type, int) or str(product_type).isdigit():
        cur.execute("""
            SELECT id, nome, categoria
            FROM tipo_produto
            WHERE id = %s
        """, (int(product_type),))
    else:
        cur.execute("""
            SELECT id, nome, categoria
            FROM tipo_produto
            WHERE LOWER(nome) = %s
               OR LOWER(categoria) = %s
               OR LOWER(REPLACE(nome, ' ', '_')) = %s
               OR LOWER(REPLACE(categoria, ' ', '_')) = %s
        """, (product, product, product, product))

    return cur.fetchone()


def parse_iso_date(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def parse_iso_datetime(value):
    try:
        return datetime.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def validity_interval(product_name, travel_date):
    product = normalize_product_type(product_name)

    if product in ('monthly_pass', 'monthly_student_pass', 'monthly_senior_pass'):
        start = datetime.datetime.combine(
            travel_date.replace(day=1),
            datetime.time.min
        )

        if travel_date.month == 12:
            next_month = datetime.date(travel_date.year + 1, 1, 1)
        else:
            next_month = datetime.date(travel_date.year, travel_date.month + 1, 1)

        return start, datetime.datetime.combine(next_month, datetime.time.min)

    start = datetime.datetime.combine(travel_date, datetime.time.min)

    if product == 'daily':
        return start, start + datetime.timedelta(days=1)

    return start, start + datetime.timedelta(days=1)


## =======================================================
## 10. PURCHASE TICKET/PASS
## =======================================================
@app.route('/dbproj/purchase', methods=['POST'])
@token_required
def purchase_ticket(current_user):

    logger.info('POST /dbproj/purchase')

    if current_user['role'] != 'cliente':
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Customers only'
        }), 403

    payload = request.get_json()
    if not payload or not all(k in payload for k in ("line_id", "product_type", "travel_date")):
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Missing fields'
        }), 400

    travel_date = parse_iso_date(payload['travel_date'])
    if travel_date is None:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Invalid travel_date'
        }), 400

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id FROM linha WHERE id = %s", (payload['line_id'],))
        if not cur.fetchone():
            conn.rollback()
            return jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Invalid line_id'
            }), 400

        product = fetch_product_type(cur, payload['product_type'])
        if not product:
            conn.rollback()
            return jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Invalid product_type'
            }), 400

        product_id, product_name = product[0], product[1]

        cur.execute("""
            SELECT
                t.preco,
                COALESCE((
                    SELECT MAX(p.percent_desconto)
                    FROM promocao p
                    WHERE p.linha_id = %s
                      AND p.tipo_produto_id = %s
                      AND %s::date BETWEEN p.data_inicio AND p.data_fim
                ), 0) AS discount_percent
            FROM tarifario t
            WHERE t.tipo_produto_id = %s
              AND t.inicio_vigencia <= %s::date
              AND (t.fim_vigencia IS NULL OR t.fim_vigencia >= %s::date)
            ORDER BY t.inicio_vigencia DESC
            LIMIT 1
        """, (
            payload['line_id'],
            product_id,
            travel_date,
            product_id,
            travel_date,
            travel_date
        ))

        fare = cur.fetchone()
        if not fare:
            conn.rollback()
            return jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'No active fare for this product_type and date'
            }), 400

        base_price = float(fare[0])
        discount_percent = float(fare[1])
        final_price = round(base_price * (1 - discount_percent / 100), 2)
        start_validity, end_validity = validity_interval(product_name, travel_date)

        cur.execute("""
            INSERT INTO titulo_viagem (
                cliente_id,
                linha_id,
                tipo_produto_id,
                data_compra,
                inicio_validade,
                fim_validade,
                preco_pago
            )
            VALUES (%s, %s, %s, NOW(), %s, %s, %s)
            RETURNING id
        """, (
            current_user['id'],
            payload['line_id'],
            product_id,
            start_validity,
            end_validity,
            final_price
        ))

        purchase_id = cur.fetchone()[0]
        conn.commit()

        response = {
            'status': StatusCodes['success'],
            'errors': None,
            'results': {
                'purchase_id': purchase_id,
                'final_price': final_price
            }
        }

    except psycopg2.Error as error:
        conn.rollback()
        error_message = str(error).strip()
        status = StatusCodes['api_error'] if 'Saldo insuficiente' in error_message else StatusCodes['internal_error']
        response = {
            'status': status,
            'errors': error_message
        }
    except Exception as error:
        conn.rollback()
        response = {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


## =======================================================
## 11. VALIDATE/USE TICKET
## =======================================================
@app.route('/dbproj/ticket/use/<int:ticket_id>', methods=['POST'])
@token_required
def use_ticket(current_user, ticket_id):

    logger.info(f'POST /dbproj/ticket/use/{ticket_id}')

    if current_user['role'] != 'cliente':
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Customers only'
        }), 403

    payload = request.get_json()
    if not payload or 'used_at' not in payload or 'station_id' not in payload:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Missing fields'
        }), 400

    used_at = parse_iso_datetime(payload['used_at'])
    if used_at is None:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Invalid used_at'
        }), 400

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT
                tv.id,
                tv.linha_id,
                tp.nome,
                tv.inicio_validade,
                tv.fim_validade
            FROM titulo_viagem tv
            JOIN tipo_produto tp ON tp.id = tv.tipo_produto_id
            WHERE tv.id = %s
              AND tv.cliente_id = %s
            FOR UPDATE OF tv
        """, (ticket_id, current_user['id']))

        ticket = cur.fetchone()
        if not ticket:
            conn.rollback()
            return jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Ticket not found for this customer'
            }), 400

        line_id = ticket[1]
        product_name = normalize_product_type(ticket[2])

        if used_at < ticket[3] or used_at >= ticket[4]:
            conn.rollback()
            return jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Ticket is outside its validity period'
            }), 400

        cur.execute("""
            SELECT 1
            FROM estacao_linha
            WHERE linha_id = %s
              AND estacao_id = %s
        """, (line_id, payload['station_id']))

        if not cur.fetchone():
            conn.rollback()
            return jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Station does not belong to the ticket line'
            }), 400

        if product_name == 'single_trip':
            cur.execute("""
                SELECT 1
                FROM validacao
                WHERE titulo_viagem_id = %s
                LIMIT 1
            """, (ticket_id,))

            if cur.fetchone():
                conn.rollback()
                return jsonify({
                    'status': StatusCodes['api_error'],
                    'errors': 'Single trip ticket already used'
                }), 400

        cur.execute("""
            SELECT id, capacidade_atual
            FROM viagem
            WHERE linha_id = %s
              AND data_hrpartida::date = %s::date
              AND data_hrpartida BETWEEN %s::timestamp - INTERVAL '30 minutes'
                                     AND %s::timestamp + INTERVAL '60 minutes'
            ORDER BY ABS(EXTRACT(EPOCH FROM (data_hrpartida - %s::timestamp)))
            LIMIT 1
            FOR UPDATE
        """, (line_id, used_at, used_at, used_at, used_at))

        trip = cur.fetchone()
        if not trip:
            conn.rollback()
            return jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'No trip found for that line near used_at'
            }), 400

        cur.execute("""
            SELECT COUNT(*)
            FROM validacao
            WHERE viagem_id = %s
        """, (trip[0],))

        used_capacity = cur.fetchone()[0]
        if used_capacity >= trip[1]:
            conn.rollback()
            return jsonify({
                'status': StatusCodes['api_error'],
                'errors': 'Trip is full'
            }), 400

        cur.execute("""
            INSERT INTO validacao (
                titulo_viagem_id,
                estacao_id,
                viagem_id,
                data_hora
            )
            VALUES (%s, %s, %s, %s)
        """, (
            ticket_id,
            payload['station_id'],
            trip[0],
            used_at
        ))

        conn.commit()
        response = {
            'status': StatusCodes['success'],
            'errors': None
        }

    except Exception as error:
        conn.rollback()
        response = {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


## =======================================================
## 12. PEAK AND LOW DEMAND PERIODS
## =======================================================
@app.route('/dbproj/report/demand', methods=['GET'])
@token_required
def report_demand(current_user):

    logger.info('GET /dbproj/report/demand')

    if current_user['role'] not in ['admin', 'super_admin']:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Forbidden'
        }), 403

    conn = db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT demand.line_id, demand.time_slot, demand.validations
            FROM (
                SELECT
                    v.linha_id AS line_id,
                    LPAD(EXTRACT(HOUR FROM val.data_hora)::int::text, 2, '0') ||
                        ':00-' ||
                    LPAD(EXTRACT(HOUR FROM val.data_hora)::int::text, 2, '0') ||
                        ':59' AS time_slot,
                    COUNT(*) AS validations
                FROM validacao val
                JOIN viagem v ON v.id = val.viagem_id
                GROUP BY v.linha_id, EXTRACT(HOUR FROM val.data_hora)::int
            ) demand
            WHERE demand.validations = (
                SELECT MAX(max_demand.validations)
                FROM (
                    SELECT
                        v2.linha_id AS line_id,
                        COUNT(*) AS validations
                    FROM validacao val2
                    JOIN viagem v2 ON v2.id = val2.viagem_id
                    GROUP BY v2.linha_id, EXTRACT(HOUR FROM val2.data_hora)::int
                ) max_demand
                WHERE max_demand.line_id = demand.line_id
            )
            OR demand.validations = (
                SELECT MIN(min_demand.validations)
                FROM (
                    SELECT
                        v3.linha_id AS line_id,
                        COUNT(*) AS validations
                    FROM validacao val3
                    JOIN viagem v3 ON v3.id = val3.viagem_id
                    GROUP BY v3.linha_id, EXTRACT(HOUR FROM val3.data_hora)::int
                ) min_demand
                WHERE min_demand.line_id = demand.line_id
            )
            ORDER BY demand.line_id, demand.validations DESC, demand.time_slot
        """

        cur.execute(query)
        rows = cur.fetchall()

        response = {
            'status': StatusCodes['success'],
            'errors': None,
            'results': [
                {
                    'line_id': row[0],
                    'time_slot': row[1],
                    'validations': row[2]
                }
                for row in rows
            ]
        }

    except Exception as error:
        response = {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


## =======================================================
## 13. TOP SPENDERS BY LINE
## =======================================================
@app.route('/dbproj/report/top_spenders', methods=['GET'])
@token_required
def report_top_spenders(current_user):

    logger.info('GET /dbproj/report/top_spenders')

    if current_user['role'] not in ['admin', 'super_admin']:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Forbidden'
        }), 403

    conn = db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT spending.line_id, spending.customer_id, u.nome, spending.spent
            FROM (
                SELECT
                    tv.linha_id AS line_id,
                    tv.cliente_id AS customer_id,
                    SUM(tv.preco_pago) AS spent
                FROM titulo_viagem tv
                WHERE tv.data_compra >= NOW() - INTERVAL '30 days'
                GROUP BY tv.linha_id, tv.cliente_id
            ) spending
            JOIN utilizador u ON u.id = spending.customer_id
            WHERE spending.spent = (
                SELECT MAX(line_spending.spent)
                FROM (
                    SELECT
                        tv2.linha_id AS line_id,
                        tv2.cliente_id AS customer_id,
                        SUM(tv2.preco_pago) AS spent
                    FROM titulo_viagem tv2
                    WHERE tv2.data_compra >= NOW() - INTERVAL '30 days'
                    GROUP BY tv2.linha_id, tv2.cliente_id
                ) line_spending
                WHERE line_spending.line_id = spending.line_id
            )
            ORDER BY spending.line_id, spending.customer_id
        """

        cur.execute(query)
        rows = cur.fetchall()

        response = {
            'status': StatusCodes['success'],
            'errors': None,
            'results': [
                {
                    'line_id': row[0],
                    'customer_id': row[1],
                    'customer_name': row[2],
                    'spent': float(row[3])
                }
                for row in rows
            ]
        }

    except Exception as error:
        response = {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


## =======================================================
## 14. GENERATE MONTHLY REPORT
## =======================================================
@app.route('/dbproj/report/monthly', methods=['GET'])
@token_required
def report_monthly(current_user):

    logger.info('GET /dbproj/report/monthly')

    if current_user['role'] not in ['admin', 'super_admin']:
        return jsonify({
            'status': StatusCodes['api_error'],
            'errors': 'Forbidden'
        }), 403

    conn = db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT
                customer_month.line_id,
                customer_month.month,
                COUNT(*) AS active_customers,
                SUM(CASE WHEN customer_month.validations >= 2 THEN 1 ELSE 0 END) AS repeat_customers
            FROM (
                SELECT
                    v.linha_id AS line_id,
                    EXTRACT(MONTH FROM val.data_hora)::int AS month,
                    tv.cliente_id AS customer_id,
                    COUNT(*) AS validations
                FROM validacao val
                JOIN viagem v ON v.id = val.viagem_id
                JOIN titulo_viagem tv ON tv.id = val.titulo_viagem_id
                GROUP BY
                    v.linha_id,
                    EXTRACT(MONTH FROM val.data_hora)::int,
                    tv.cliente_id
            ) customer_month
            GROUP BY customer_month.line_id, customer_month.month
            ORDER BY customer_month.line_id, customer_month.month
        """

        cur.execute(query)
        rows = cur.fetchall()

        response = {
            'status': StatusCodes['success'],
            'errors': None,
            'results': [
                {
                    'line_id': row[0],
                    'month': row[1],
                    'active_customers': row[2],
                    'repeat_customers': row[3]
                }
                for row in rows
            ]
        }

    except Exception as error:
        response = {
            'status': StatusCodes['internal_error'],
            'errors': str(error)
        }
    finally:
        if conn is not None:
            conn.close()

    return jsonify(response)


if __name__ == '__main__':
    logging.basicConfig(filename='log_file.log')
    logger = logging.getLogger('logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s]:  %(message)s', '%H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    host = '127.0.0.1'
    port = 8080
    
    logger.info(f'Starting API on http://{host}:{port}')
    app.run(host=host, debug=True, threaded=True, port=port)
