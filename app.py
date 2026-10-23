import os
import json
import urllib.request
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'family-hub-forever-secure-token-permanent'

# 100년 영구 로그인 세션 설정
PERMANENT_DAYS = 365 * 100
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=PERMANENT_DAYS)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=PERMANENT_DAYS)
app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Render PostgreSQL DB 연동
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'family_local.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- 데이터 모델 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    birthday = db.Column(db.String(20), default='')

class Praise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    receiver = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Diary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    content = db.Column(db.String(200), nullable=False)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.filter_by(id=int(user_id)).first()
    except Exception:
        return None

with app.app_context():
    db.create_all()

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=PERMANENT_DAYS)

# --- 메인 페이지 ---
@app.route('/')
@login_required
def index():
    users = User.query.all()
    my_praises = Praise.query.filter_by(receiver=current_user.username).order_by(Praise.created_at.desc()).all()
    diaries = Diary.query.filter_by(user_id=current_user.id).order_by(Diary.created_at.desc()).all()
    todos = Todo.query.filter_by(user_id=current_user.id).all()
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    chat_messages = ChatMessage.query.order_by(ChatMessage.created_at.asc()).all()
    
    return render_template('index.html', 
                           user=current_user, 
                           all_users=users,
                           my_praises=my_praises,
                           diaries=diaries,
                           todos=todos,
                           notices=notices,
                           chat_messages=chat_messages)

# --- 실시간 무새로고침 API ---
@app.route('/api/live_sync', methods=['GET'])
@login_required
def live_sync():
    chats = ChatMessage.query.order_by(ChatMessage.created_at.asc()).limit(50).all()
    chat_list = [{
        'id': c.id,
        'sender': c.sender,
        'message': c.message,
        'time': c.created_at.strftime('%H:%M'),
        'is_me': (c.sender == current_user.username)
    } for c in chats]

    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    notice_list = [{
        'id': n.id,
        'author': n.author,
        'content': n.content,
        'time': n.created_at.strftime('%Y-%m-%d %H:%M')
    } for n in notices]

    praises = Praise.query.filter_by(receiver=current_user.username).order_by(Praise.created_at.desc()).all()
    praise_list = [{
        'id': p.id,
        'sender': p.sender,
        'content': p.content,
        'time': p.created_at.strftime('%Y-%m-%d %H:%M')
    } for p in praises]

    return jsonify({
        'chats': chat_list,
        'notices': notice_list,
        'praises': praise_list
    })

@app.route('/api/chat/send', methods=['POST'])
@login_required
def send_chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if message:
        new_msg = ChatMessage(sender=current_user.username, message=message)
        db.session.add(new_msg)
        db.session.commit()
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'fail'}), 400

# --- 똑똑한 대화형 AI 도우미 API ---
@app.route('/api/ai_chat', methods=['POST'])
@login_required
def ai_chat():
    data = request.get_json() or {}
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'reply': '궁금한 점이나 도움이 필요한 내용을 입력해 주세요!'}), 400

    api_key = os.environ.get('GEMINI_API_KEY')
    
    # 1. Gemini API Key가 Render 환경변수에 등록되어 있을 경우 최고 성능 모델 호출
    if api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"너는 화목하고 따뜻한 가족 전용 웹사이트의 만능 AI 비서야. 사용자의 이름은 '{current_user.username}'님이야. 일상 대화, 공부, 요리, 컴퓨터 지식, 고민 상담 등 사용자가 묻는 모든 질문에 대해 친절하고 명확하며 알기 쉽게 한국어로 답변해줘. 질문: {prompt}"
                    }]
                }]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                ai_text = res_data['candidates'][0]['content']['parts'][0]['text']
                return jsonify({'reply': ai_text})
        except Exception:
            pass

    # 2. API Key 미등록 시 자체 스마트 지식 백과 엔진으로 구동
    p_lower = prompt.lower()
    if any(k in p_lower for k in ["안녕", "반가워", "하이"]):
        reply = f"안녕하세요, {current_user.username}님! 오늘 하루는 어떠셨나요? 궁금한 점이 있거나 도움이 필요하시면 무엇이든 편하게 물어보세요."
    elif any(k in p_lower for k in ["뭐해", "역할", "누구"]):
        reply = f"저는 {current_user.username}님 가족 전용 스마트 AI 비서예요! 일상 질문 답변, 상식 지식 검색, 요리 레시피 추천, 고민 상담, 글 작성 도우미 역할을 해드립니다."
    elif any(k in p_lower for k in ["저녁", "점심", "아침", "메뉴", "밥", "식사", "배고파"]):
        menus = ["칼칼하고 깊은 국물의 김치찌개와 바삭한 계란말이", "가족 다 함께 둘러앉아 굽는 삼겹살", "구수한 된장찌개와 고등어구이", "간편하고 든든한 소고기 볶음밥", "매콤달콤한 떡볶이와 바삭한 모둠튀김"]
        import random
        reply = f"{current_user.username}님, 오늘의 추천 식사 메뉴는 **{random.choice(menus)}**입니다! 가족들과 함께 맛있는 식사 시간 되세요. 🍲"
    elif any(k in p_lower for k in ["심심", "놀거리", "게임", "휴식"]):
        reply = "가족들과 함께 가벼운 끝말잇기 게임, 보드게임 한 판, 또는 좋아하는 음악을 틀고 산책을 다녀오는 것은 어떠세요? 🎲"
    elif any(k in p_lower for k in ["고마워", "감사", "수고"]):
        reply = f"도움이 되어 기쁩니다! 언제든 필요한 게 있으시면 망설이지 말고 말씀해 주세요, {current_user.username}님. 😊"
    else:
        reply = f"'{prompt}'에 대해 물어보셨군요! 더 심층적이고 폭넓은 전문 지식 검색과 실시간 추론을 완벽하게 활성화하려면, Render 환경변수에 무료 `GEMINI_API_KEY`를 추가하시면 최신 AI 두뇌로 바로 업그레이드됩니다. 현재도 가족 비서 기능은 상시 대기 중입니다! ✨"

    return jsonify({'reply': reply})

# --- 로그인 / 회원가입 ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True, duration=timedelta(days=PERMANENT_DAYS))
            return redirect(url_for('index'))
        flash('아이디 또는 비밀번호가 일치하지 않습니다.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        invite_code = (request.form.get('invite_code') or '').strip()
        if invite_code != '서희스타일스':
            flash('가족 초대 코드가 올바르지 않습니다.')
            return redirect(url_for('login'))
            
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        
        if not username or not password:
            flash('아이디와 비밀번호를 모두 입력해 주세요.')
            return redirect(url_for('login'))
            
        if User.query.filter_by(username=username).first():
            flash('이미 존재하는 아이디입니다.')
            return redirect(url_for('login'))
            
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user, remember=True, duration=timedelta(days=PERMANENT_DAYS))
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/set_birthday', methods=['POST'])
@login_required
def set_birthday():
    year = request.form.get('year')
    month = request.form.get('month')
    day = request.form.get('day')
    if year and month and day:
        current_user.birthday = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_praise', methods=['POST'])
@login_required
def add_praise():
    receiver = (request.form.get('receiver') or '').strip()
    content = (request.form.get('content') or '').strip()
    if receiver and content:
        new_praise = Praise(sender=current_user.username, receiver=receiver, content=content)
        db.session.add(new_praise)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_diary', methods=['POST'])
@login_required
def add_diary():
    content = (request.form.get('content') or '').strip()
    if content:
        new_diary = Diary(user_id=current_user.id, content=content)
        db.session.add(new_diary)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_todo', methods=['POST'])
@login_required
def add_todo():
    content = (request.form.get('content') or '').strip()
    if content:
        new_todo = Todo(user_id=current_user.id, content=content)
        db.session.add(new_todo)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_notice', methods=['POST'])
@login_required
def add_notice():
    content = (request.form.get('content') or '').strip()
    if content:
        new_notice = Notice(author=current_user.username, content=content)
        db.session.add(new_notice)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
