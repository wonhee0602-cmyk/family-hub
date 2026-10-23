import os
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'family-hub-forever-secure-token-permanent'

# 배포 버전 타임스탬프 (무새로고침 핫 업데이트용)
APP_BUILD_VERSION = str(int(time.time()))

# 100년 영구 로그인 세션
PERMANENT_DAYS = 365 * 100
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=PERMANENT_DAYS)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=PERMANENT_DAYS)
app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 데이터베이스 영구 경로 보존
data_dir = os.environ.get('RENDER_DATA_PATH')
if not data_dir:
    data_dir = os.path.abspath(os.path.dirname(__file__))
os.makedirs(data_dir, exist_ok=True)
db_path = os.path.join(data_dir, 'family_permanent.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
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

# --- 버전 체크 API (무새로고침 자동 최신화) ---
@app.route('/api/version')
def get_version():
    return jsonify({'version': APP_BUILD_VERSION})

# --- AI 비서 질의응답 API ---
@app.route('/api/ask_ai', methods=['POST'])
@login_required
def ask_ai():
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'answer': '질문을 입력해 주세요.'})
    
    # 가족 허브 전용 똑똑한 스마트 봇 응답 로직
    q_lower = question.lower()
    if '안녕' in q_lower or '반가' in q_lower:
        ans = f"반가워요, {current_user.username}님! 우리 가족 홈 AI 비서입니다. 무엇이든 편하게 물어보세요."
    elif '시간' in q_lower or '몇 시' in q_lower or '날짜' in q_lower:
        now_str = datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')
        ans = f"현재 대한민국 표준시 기준 {now_str} 입니다."
    elif '생일' in q_lower:
        users_with_bday = User.query.filter(User.birthday != '').all()
        if users_with_bday:
            bday_info = ", ".join([f"{u.username}({u.birthday})" for u in users_with_bday])
            ans = f"등록된 가족 생일 목록입니다: {bday_info}"
        else:
            ans = "아직 생일이 등록된 가족이 없습니다. 우측 상단 닉네임을 눌러 생년월일을 등록해 보세요!"
    elif '기능' in q_lower or '도움말' in q_lower:
        ans = "우리 가족 홈에서는 📢실시간 공지사항 공유, 💬가족 실시간 채팅, 💌칭찬 우편함, ✅나만의 할 일, 📖비밀 일기 작성이 가능합니다."
    else:
        # 일반 지식 및 궁금한 질문에 대한 자동 안내
        ans = f"'{question}'에 대해 질문해 주셨군요! 가족 관련 일정이나 기록은 언제든 저에게 물어보세요. 원하시는 특정 정보나 계산도 친절히 답변해 드립니다."

    return jsonify({'answer': ans})

# --- 라우트 ---
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
                           chat_messages=chat_messages,
                           build_version=APP_BUILD_VERSION)

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
        'version': APP_BUILD_VERSION,
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
    app.run(host='0.0.0.0', port=5000)
