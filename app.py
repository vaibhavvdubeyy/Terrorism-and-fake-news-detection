from flask import Flask,render_template,request,session,flash,redirect,url_for,send_from_directory,flash
from email.mime.text import MIMEText
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import random, copy
import smtplib
import requests
import string
import random
from werkzeug.utils import secure_filename
import os
from database import db,User,Post,follows,liketab
from flask_mail import Mail
from datetime import datetime
from passlib.hash import sha256_crypt
import tensorflow as tf
import joblib
import numpy as np
from keras.preprocessing import image
from chat import app1
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_session import Session
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
import preprocessor as p
import re

app=Flask(__name__)
# loaded_model = joblib.load('./pipeline.sav')
loaded_model = pickle.load(open('model.pkl', 'rb'))
loaded_model1 = pickle.load(open('terro_text.sav', 'rb'))
tfvect = TfidfVectorizer(stop_words='english', max_df=0.7)
dataframe = pd.read_csv('news.csv')
x = dataframe['text']
y = dataframe['label']
x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=0)
train = pd.read_csv("train.csv")
test = pd.read_csv("test.csv")
y1 = train.label.values


vectorizer = CountVectorizer(binary=True, stop_words='english')

REPLACE_NO_SPACE = re.compile("(\.)|(\;)|(\:)|(\!)|(\')|(\?)|(\,)|(\")|(\|)|(\()|(\))|(\[)|(\])|(\%)|(\$)|(\>)|(\<)|(\{)|(\})")
REPLACE_WITH_SPACE = re.compile("(<br\s/><br\s/?)|(-)|(/)|(:).")


def clean_tweets(df):
  tempArr = []
  for line in df:
    # send to tweet_processor
    tmpL = p.clean(line)
    # remove puctuation
    tmpL = REPLACE_NO_SPACE.sub("", tmpL.lower()) # convert all tweets to lower cases
    tmpL = REPLACE_WITH_SPACE.sub(" ", tmpL)
    tempArr.append(tmpL)
  return tempArr

train_tweet = clean_tweets(train["tweet"])
train_tweet = pd.DataFrame(train_tweet)
train["clean_tweet"] = train_tweet
x_train1, x_test1, y_train1, y_test1 = train_test_split(train.clean_tweet.values, y1, stratify=y1, random_state=1, test_size=0.3, shuffle=True)


# learn a vocabulary dictionary of all tokens in the raw documents
vectorizer.fit(list(x_train1) + list(x_test1))
x_train_vec = vectorizer.transform(x_train)
x_test_vec = vectorizer.transform(x_test)


app.config['SESSION_TYPE'] = 'filesystem'
app.debug = True
Session(app)
socketio = SocketIO(app, manage_session=False)

model = tf.keras.models.load_model('model.h5') 
app.config['UPLOAD_FOLDER']=r'static\uploads'
app.secret_key='United'
#app.config['SQLALCHEMY_DATABASE_URI']='postgresql://postgres:saksham@localhost/minor'
app.config['SQLALCHEMY_DATABASE_URI']='postgres://ykznxsdzcebfil:d1f44feba03fada8da02d88a302da48ac1544efbbf301f9a47361ac1fde07ea9@ec2-54-159-175-113.compute-1.amazonaws.com:5432/ddqgp9nsn8aj32?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = "psp51790@gmail.com",
    MAIL_PASSWORD=  "ps*123456"
)
mail = Mail(app)

i=0
db.init_app(app)
with app.app_context():
    db.create_all()

@app.route("/",methods=['GET', 'POST'])
def index():
    return render_template("index.html")

@app.route("/login", methods = ['GET', 'POST'])
def login():
    if(request.method=='POST'):
        Custname = request.form.get('user')
        Custpass = request.form.get('pass')
        getinfo = db.session.query(User).filter_by(uname=Custname).first()
        
        if Custname=="admin" and Custpass=="admin":
            session['user'] = "admin"
            return render_template('admindashboard.html',name=Custname)
        if getinfo.terror_count>=3:
            return render_template("index.html",mess="Your Account has been deactivated please contact Us at our mail")    
        elif sha256_crypt.verify(Custpass, getinfo.passw):
            session['user'] = Custname
            session['uid']=getinfo.uid
            b=session['uid']
            a = db.session.execute("SELECT * FROM follows WHERE uid_who=:param ",{"param": b})
            names = [row[1] for row in a]
            c,d=[],[]
            for i in names :
                getinfo = db.session.query(User).filter_by(uid=i).order_by(func.random()).all()
                c.append(getinfo[0])
            for j in c:
                get = db.session.query(Post).filter_by(uid=j.uid,active=1).order_by(Post.pdate.desc()).all()
                d.append(get)
            getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()
            return render_template("homepagenew.html",unam=session['user'],c=zip(c,d),u=getinfo1)
        else:
            return render_template('index.html')

@app.route("/logout")  
def logout():
    
    session.pop('user', None)
    return redirect("/")


@app.route("/signup", methods = ['GET', 'POST'])
def signup():
    if(request.method=='POST'):
        uname = request.form.get('uname')
        name = request.form.get('name')
        passw = request.form.get('passw')
        rpassw = request.form.get('rpassw')
        email= request.form.get('email')
        phno = request.form.get('phno')
        info=db.session.query(User).filter_by(uname=uname).count()
        if passw==rpassw and info!=1:
            passs=sha256_crypt.encrypt(passw)
            user1=User(passw=passs,uName=uname,name=name,cont=phno,ema=email,descrp="Hi There I am using Duel ",profile="static/uploads/t67.jpg")
            db.session.add(user1)
            db.session.commit()
            return render_template("index.html",mess="Congratulation,Account has been created")
        else:
            return "Username Already Exist"

@app.route("/forget",methods = ['GET', 'POST'])
def forget():
    return render_template("forget.html")
    
@app.route("/reset",methods = ['GET', 'POST'])  
def reset():
    uname=request.form.get('uname')
    email = request.form.get('email')
    getinfo = User.query.filter_by(uname=uname,email=email)
    smail="psp51790@gmail.com"
    if getinfo.count()==1:
        pas=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))
        type(getinfo)
        message="Hello There %s .<br>Your Password has been generated .<br>Your password is <strong>%s</strong>.<br>Please login with this password to change password"%(uname,pas)
        #msg=MIMEText(message,'html')
        getinfo.update(dict(passw=pas))
        db.session.commit()
        mail.send_message(subject="Password Generated",html=message,sender=smail,recipients = [email])
        return "Hello"
    else:
        return "Hi"  

def fake_news_det(news):
    tfid_x_train = tfvect.fit_transform(x_train)
    tfid_x_test = tfvect.transform(x_test)
    input_data = [news]
    vectorized_input_data = tfvect.transform(input_data)
    prediction = loaded_model.predict(vectorized_input_data)
    return prediction

@app.route("/upload",methods=['POST','GET'])
def upload():
    if (request.method =="POST"):
        user=session['uid']
        f=request.files['file']
        ptitle=request.form.get('ptitle')
        pdesc=request.form.get('desc')
        i=0
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
        path=str(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
        # result = loaded_model.predict([[pdesc]])

        a=[pdesc]
        b=vectorizer.transform(a)
        c=loaded_model1.predict(b)        
        result=fake_news_det(pdesc)

        print(c)
        print(result)
        
        test_image = image.load_img(path, target_size = (64, 64))
        test_image = image.img_to_array(test_image)
        test_image = np.expand_dims(test_image, axis = 0)
        result1 = model.predict(test_image/255.0)
        if  result1[0][0]  >0.6  or c==[1]:
            prediction = 'terror'
            i=0
            getinfo=db.session.query(User).filter_by(uid=user)
            uname=getinfo.first().name
            k=getinfo.first().terror_count
            k+=1
            print(k)
            getinfo.update({User.terror_count:k})
            db.session.commit()
            smail="psp51790@gmail.com"
            email=getinfo.first().email
            message="Hello There %s .<br>Your post has been detected as terrorist related post .<br>Please reply at this email if not intentionaly done by you "%(uname)
            mail.send_message(subject="Terrorism detected",html=message,sender=smail,recipients = [email])
        else:
            prediction = 'person'
            i=1
        print(prediction)
        post=Post(ptitle=ptitle,pdate=datetime.now(),pdesc=pdesc,uid=session['uid'],pimgpath=path,likes=0,active=i)  
        db.session.add(post)
        db.session.commit()
        b=session['uid']
        a = db.session.execute("SELECT * FROM follows WHERE uid_who=:param ",{"param": b})
        names = [row[1] for row in a]
        c,d=[],[]
        getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()
        for i in names :
            getinfo = db.session.query(User).filter_by(uid=i).order_by(func.random()).all()
            c.append(getinfo[0])
        for j in c:
            get = db.session.query(Post).filter_by(uid=j.uid,active=1).order_by(Post.pdate.desc()).all()
            d.append(get)
        if prediction =='person':
            return render_template("homepagenew.html",unam=session['user'],u=getinfo1,mesg="Post Uploaded Successfully",c=zip(c,d))
        else:
            return render_template("homepagenew.html",unam=session['user'],u=getinfo1,mesg="Terrorism Detected.....",c=zip(c,d))
    else:
        getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()
        return render_template("homepagenew.html",unam=session['user'],u=getinfo1,mesg="Some Error Occured Please Try Again",c=zip(c,d))

@app.route("/uploadNews",methods=['POST','GET'])
def uploadNews():
    if (request.method =="POST"):
        user=session['uid']
        ptitle=request.form.get('newsT')
        pdesc=request.form.get('newsD')
        i=0
        # f.save(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
        # path=str(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
        # result = loaded_model.predict([[pdesc]])

        a=[pdesc]
        b=vectorizer.transform(a)
        c=loaded_model1.predict(b)        
        result=fake_news_det(pdesc)

        print(c)
        print(result)
        
        
        if result==['FAKE'] :
            prediction = 'terror'
            i=0
            getinfo=db.session.query(User).filter_by(uid=user)
            uname=getinfo.first().name
            k=getinfo.first().terror_count
            k+=1
            print(k)
            getinfo.update({User.terror_count:k})
            db.session.commit()
            smail="psp51790@gmail.com"
            email=getinfo.first().email
            message="Hello There %s .<br>Your post has been detected as Fake .<br>Please reply at this email if not intentionaly done by you "%(uname)
            mail.send_message(subject="Fake News detected",html=message,sender=smail,recipients = [email])
        else:
            prediction = 'person'
            i=1
        print(prediction)
        post=Post(ptitle=ptitle,pdate=datetime.now(),pdesc=pdesc,uid=session['uid'],pimgpath="static/uploads/News.jpg",likes=0,active=i)  
        db.session.add(post)
        db.session.commit()
        b=session['uid']
        a = db.session.execute("SELECT * FROM follows WHERE uid_who=:param ",{"param": b})
        names = [row[1] for row in a]
        c,d=[],[]
        getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()
        for i in names :
            getinfo = db.session.query(User).filter_by(uid=i).order_by(func.random()).all()
            c.append(getinfo[0])
        for j in c:
            get = db.session.query(Post).filter_by(uid=j.uid,active=1).order_by(Post.pdate.desc()).all()
            d.append(get)
        if prediction =='person':
            return render_template("homepagenew.html",unam=session['user'],u=getinfo1,mesg="Post Uploaded Successfully",c=zip(c,d))
        else:
            return render_template("homepagenew.html",unam=session['user'],u=getinfo1,mesg="Fake News Detected.....",c=zip(c,d))
    else:
        getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()
        return render_template("homepagenew.html",unam=session['user'],u=getinfo1,mesg="Some Error Occured Please Try Again",c=zip(c,d))

@app.route("/uploadPost",methods=['POST','GET'])
def uploadPost():
    return render_template("upload.html")    

@app.route("/displayPost/<posttype>",methods=['POST','GET'])
def displayPost(posttype):
    if posttype=="fair":
        info=db.session.query(Post).filter_by(active=1).all()
        return render_template("test.html",post=info)
    if posttype=="blocked":
        info=db.session.query(Post).filter_by(active=0).all()
        return render_template("test.html",post=info,postType=['blocked'])
    if posttype=="critical":
        info=db.session.query(User).filter_by(terror_count=2).all()
        return render_template("userlist.html",info=info)
    if posttype=="blockedusr":
        info=db.session.query(User).filter_by(terror_count=3).all()
        return render_template("userlist.html",info=info)





@app.route('/display/<filename>')
def display_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename=filename)

@app.route('/userlist')
def userlist():
    info=db.session.query(User)
    return render_template('userlist.html',info=info)

@app.route("/adminDashboard",methods=['POST','GET'])
def adminDashBoard():
    return render_template("upload.html") 

@app.route("/deletePost/<string:id>",methods=['POST'])
def deletePost(id):
    db.session.query(Post).filter_by(pid=id).delete()
    db.session.commit()
    return render_template('admindashboard.html')

@app.route("/MarkasfairPost/<string:id>",methods=['POST'])
def MarkasfairPost(id): #foregin key
    db.session.query(Post).filter_by(pid=id).update({Post.active:1})
    getinfo=  db.session.query(Post).filter_by(pid=id).first()
    userid=getinfo.uid
    getinfo1=  db.session.query(User).filter_by(uid=userid).first()
    terror_count=getinfo1.terror_count
    terror_count-=1
    db.session.query(User).filter_by(uid=userid).update({User.terror_count:terror_count})
    db.session.commit() 
    return render_template('admindashboard.html')


@app.route("/followUser",methods=['POST'])
def followUser():
    getinfo = db.session.query(User).all()
    getinfo2= db.session.query(User).filter_by(uid=session['uid']).first()
    return render_template("Following.html",users=getinfo,unam=session['user'],u=getinfo2)  

 

@app.route("/follow/<string:id>",methods=['POST'])
def follow(id):
    user=session['uid']
    statement = follows.insert().values(uid_who=user, uid_whom=id)
    db.session.execute(statement)
    db.session.commit()
    getinfo=db.session.query(User).filter_by(uid=user)
    getinfo1=db.session.query(User).filter_by(uid=id)
    i=getinfo.first().following_count
    i+=1
    getinfo.update({User.following_count:i})
    k=getinfo1.first().follower_count
    k+=1
    getinfo1.update({User.follower_count:k})
    db.session.commit()
    a = db.session.execute("SELECT * FROM follows WHERE uid_who=:param ",{"param": user})
    names = [row[1] for row in a]
    c,d=[],[]
    for i in names :
        getinfo = db.session.query(User).filter_by(uid=i).order_by(func.random()).all()
        c.append(getinfo[0])
    for j in c:
        get = db.session.query(Post).filter_by(uid=j.uid,active=1).order_by(Post.pdate.desc()).all()
        d.append(get)
    getinfo2= db.session.query(User).filter_by(uid=session['uid']).first()                    
    return render_template("homepagenew.html",unam=session['user'],c=zip(c,d),u=getinfo2)
    

@app.route("/followingList",methods=['GET'])
def followingList():
    b=session['uid']
    # info=follows.select().where(uid_who==b)
    a = db.session.execute("SELECT * FROM follows WHERE uid_who=:param",{"param": b})
    names = [row[1] for row in a]
    c=[]
    for i in names :
        getinfo = db.session.query(User).filter_by(uid=i).all()
        c.append(getinfo[0])
    print(c[0].uid)
    getinfo1= db.session.query(User).filter_by(uid=session['uid']).first()
    return render_template("unfollow.html",unam=session['user'],users=c,u=getinfo1)

@app.route("/followerList",methods=['GET'])
def followerList():
    b=session['uid']
    # info=follows.select().where(uid_who==b)
    a = db.session.execute("SELECT * FROM follows WHERE uid_whom=:param",{"param": b})
    names = [row[1] for row in a]
    c=[]
    for i in names :
        getinfo = db.session.query(User).filter_by(uid=i).all()
        c.append(getinfo[0])
    print(c[0].uid)
    # print(getinfo[0].uid)
    getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()
    return render_template("Following.html",users=c,u=getinfo1)

@app.route("/unfollow/<string:id>",methods=['POST'])
def unfollow(id):
    user=session['uid']
    # statement = follows.delete(uid_who=a, uid_whom=id)
    a = db.session.execute("DELETE FROM follows WHERE uid_who=:param and uid_whom=:para ",{"param": user,"para":id})
    # db.session.execute(statement)
    db.session.commit()
    getinfo=db.session.query(User).filter_by(uid=user)
    i=getinfo.first().following_count
    i-=1
    getinfo.update({User.following_count:i})

    getinfo1=db.session.query(User).filter_by(uid=id)
    k=getinfo1.first().follower_count
    k-=1
    getinfo1.update({User.follower_count:k})

    db.session.commit()
    a = db.session.execute("SELECT * FROM follows WHERE uid_who=:param ",{"param": user})
    names = [row[1] for row in a]
    c,d=[],[]
    for i in names :
        getinfo = db.session.query(User).filter_by(uid=i).order_by(func.random()).all()
        c.append(getinfo[0])
    for j in c:
        get = db.session.query(Post).filter_by(uid=j.uid,active=1).order_by(Post.pdate.desc()).all()
        d.append(get)
    getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()               
    return render_template("homepagenew.html",unam=session['user'],c=zip(c,d),u=getinfo1)

@app.route("/Myprofile",methods=['GET'])
def Myprofile():
    getinfo = db.session.query(User).filter_by(uid=session['uid']).first()
    getpost = db.session.query(Post).filter_by(uid=session['uid'],active=1).order_by(Post.pdate.desc()).all()
    return render_template("user-profile.html",users=getinfo,post=getpost)

@app.route("/like",methods=['POST','GET'])
def like():
    if (request.method =="POST"):
        f=request.form.get('pid')
        user=session['uid']
        a = db.session.execute("INSERT INTO liketab VALUES(:param,:id,:date)",{"param": user,"id":f,"date":datetime.now()})
        getinfo = db.session.query(Post).filter_by(pid=f).first()
        count=getinfo.likes
        count+=1
        db.session.query(Post).filter_by(pid=f).update({Post.likes:count})
        db.session.commit()
        return "H"
        
@app.route('/chathome', methods=['GET', 'POST'])
def chathome():
    return render_template('chatlogin.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if(request.method=='POST'):
        session['username']=session['user']
        room = request.form['room']
        #Store the data in session
        
        session['room'] = room
        return render_template('chat.html', session = session)
    else:
        if(session.get('username') is not None):
            return render_template('chat.html', session = session)
        else:
            return redirect(url_for('chathome'))

@socketio.on('join', namespace='/chat')
def join(message):
    room = session.get('room')
    join_room(room)
    emit('status', {'msg':  session.get('username') + ' has entered the room.'}, room=room)


@socketio.on('text', namespace='/chat')
def text(message):
    room = session.get('room')
    emit('message', {'msg': session.get('username') + ' : ' + message['msg']}, room=room)


@socketio.on('left', namespace='/chat')
def left(message):
    room = session.get('room')
    username = session.get('username')
    leave_room(room)
    emit('status', {'msg': username + ' has left the room.'}, room=room)

@app.route('/homepage',methods=['GET', 'POST'])
def homepage():
    user=session['uid']
    a = db.session.execute("SELECT * FROM follows WHERE uid_who=:param ",{"param": user})
    names = [row[1] for row in a]
    c,d=[],[]
    for i in names :
        getinfo = db.session.query(User).filter_by(uid=i).order_by(func.random()).all()
        c.append(getinfo[0])
    for j in c:
        get = db.session.query(Post).filter_by(uid=j.uid,active=1).order_by(Post.pdate.desc()).all()
        d.append(get)
    getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()                
    return render_template("homepagenew.html",unam=session['user'],u=getinfo1,c=zip(c,d))

@app.route('/profileimage',methods=['GET', 'POST'])
def profileimage():
    if (request.method =="POST"):
        user=session['uid']
        f=request.files['file']
        getinfo1 = db.session.query(User).filter_by(uid=session['uid']).first()
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
        path=str(os.path.join(app.config['UPLOAD_FOLDER'],secure_filename(f.filename)))
        getinfo=db.session.query(User).filter_by(uid=user)        
        getinfo.update({User.profile:path})
        db.session.commit()
        return redirect("/homepage")

@app.route("/resetPass",methods = ['GET', 'POST'])
def resetPass():
    return render_template("ResetPass.html")
    
@app.route("/reset1Pass",methods = ['GET', 'POST'])  
def reset1Pass():
    uname=request.form.get('unam')
    pas= request.form.get('email')
    a=session['uid']
    getinfo = User.query.filter_by(uid=a)
    if sha256_crypt.verify(uname, getinfo.first().passw):
        passs=sha256_crypt.encrypt(pas)
        getinfo.update(dict(passw=passs))
        db.session.commit() 
        return redirect("/homepage")


if __name__=="__main__":
    socketio.run(app)
    # app.run(debug=True)
    

