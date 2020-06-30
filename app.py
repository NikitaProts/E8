import requests
import enum
from sqlalchemy import Enum
from celery import Celery
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request

#настройка приложения и бд  
app  = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Селери 
celery = Celery(app.name, broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')


class Results(db.Model):
    _id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(300), unique=False, nullable=True)
    words_count = db.Column(db.Integer, unique=False, nullable=True)
    http_status_code = db.Column(db.Integer)


class TaskStatus (enum.Enum):
    NOT_STARTED = 1
    PENDING = 2
    FINISHED = 3

class Tasks(db.Model):
    _id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(300), unique=False, nullable=True)
    timestamp = db.Column(db.DateTime())
    task_status = db.Column(Enum(TaskStatus))
    http_status = db.Column(db.Integer)

#основной обработчик формы index.html
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':

        url_adress = request.form['url_for_parse']

        if url_adress =='':
            return 'Ссылка пуста'
        else: 
            if not url_adress.startswith('http') or not url_adress.startswith('https'):
                url_adress = 'http://' + url_adress
            value_in_db = Tasks(address=url_adress,
                            timestamp=datetime.now(), task_status='NOT_STARTED')
                            
            try: 
                db.session.add(value_in_db)
                db.session.commit()
                return render_template('index.html')
            except:
                return 'При записи произошла ошибка'
        
    else:
        return render_template('index.html')


# @app.route('/site-list')
# def site_list():
#     sites = Tasks.query.all()
#     return render_template('site_list.html', sites = sites)

# Часть с селери 
@celery.task
def parsing_func(_id):
    
    task = Tasks.query.get(_id)
    task.task_status = 'PENDING'
    db.session.commit()
    address = task.address
    with app.app_context():
        parse_url = requests.get(address)
        parse_status = parse_url.status_code
        if parse_url.ok:
            parse_url = parse_url.text.lower().split()
            words = parse_url.count('python')
        result = Results(address=address, words_count=words, http_status_code=parse_status)
        task = Tasks.query.get(_id)
        task.task_status = 'FINISHED'
        db.session.add(result)
        db.session.commit()


@app.route('/results')
def get_results():
    results = Results.query.all()
    return render_template('results.html', results=results)

        




if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
