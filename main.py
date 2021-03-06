from flask import Flask, render_template, redirect,request, url_for, flash,abort,session
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm,CreateActivityForm,AboutForm
from functools import wraps
from flask_gravatar import Gravatar
from flask_msearch import Search
from sqlalchemy import desc
from flask_paginate import Pagination, get_page_parameter
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
#app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
app.config['CKEDITOR_PKG_TYPE'] = 'full'
Bootstrap(app)



##CONNECT TO DB
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL","sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
search = Search(db=db)
search.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

gravatar = Gravatar(app,size=100,rating='g',default='retro',force_default=False,force_lower=False,
                        use_ssl=False,base_url=None)

#Create admin-only decorator
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    __searchable__ = ['title', 'body']
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    categories_id = db.Column(db.Integer, db.ForeignKey('categories.id'))

    # Create reference to the User object, the "posts" refers to the posts protperty in the User class.
    author = relationship("User", back_populates="posts")
    category = relationship("Categories",back_populates="cat_posts")

    # ***************Parent Relationship*************#
    comments = relationship("Comment",back_populates="parent_post")

##CREATE TABLE IN DB
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.

    posts = relationship("BlogPost",back_populates="author")
    comments = relationship("Comment",back_populates="comment_author")

class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    #text = db.Column(db.Text, nullable=False)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    comment_author = relationship("User", back_populates="comments")

    # ***************Child Relationship*************#

    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
    parent_post = relationship("BlogPost", back_populates="comments")
    text = db.Column(db.Text, nullable=False)

class Categories(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    summary = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    cat_posts = relationship("BlogPost", back_populates="category")


class Activities(db.Model):
    __tablename__ = "activities"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    summary = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)





#db.create_all()

##################### Search Function ##############################
@app.route('/search',methods=['GET','POST'])
def searched():
    if request.method == 'POST':
        search_words = request.form.get('searcheditem')
        results = BlogPost.query.msearch(search_words).filter()
        page = request.args.get('page', 1, type=int)
        pages = results.paginate(page=page, per_page=8)
        return render_template('index.html',all_posts=results,pages=pages)






###################### Activities Functions ##############################

@app.route('/allactivities')
def get_all_activities():
    all_activities = Activities.query.order_by(desc(Activities.id))
    page = request.args.get('page', 1, type=int)
    pages = all_activities.paginate(page=page, per_page=8)
    return render_template('all_activities.html',activities=all_activities,pages=pages)


@app.route("/activities/<int:act_id>",methods=['GET','POST'])
def show_activitiy(act_id):
    requested_act = Activities.query.get(act_id)
    return render_template('activity.html',act=requested_act)

@app.route("/new-activity",methods=['GET','POST'])
@admin_only
def add_new_activity():
    form = CreateActivityForm()
    if form.validate_on_submit():
        new_post = Activities(
            title=form.title.data,
            summary=form.summary.data,
            body=form.body.data,
            img_url=form.img_url.data,
            date = date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_activities"))
    return render_template("make-activity.html", form=form)


@app.route("/edit-activity/<int:act_id>",methods=['GET','POST'])
@admin_only
def edit_activity(act_id):
    activity = Activities.query.get(act_id)
    edit_form = CreateActivityForm(
        title=activity.title,
        summary=activity.summary,
        img_url=activity.img_url,
        body=activity.body
    )
    if edit_form.validate_on_submit():
        activity.title = edit_form.title.data
        activity.summary = edit_form.summary.data
        activity.img_url = edit_form.img_url.data
        activity.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_activitiy", act_id=activity.id))

    return render_template("make-activity.html", form=edit_form)

@app.route("/delete-activity/<int:act_id>")
@admin_only
def delete_act(act_id):
    act_to_delete = Activities.query.get(act_id)
    db.session.delete(act_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_activities'))


###################### Categories Funtions ###########################

@app.route("/category/<int:cat_id>",methods=['GET','POST'])
def show_category(cat_id):
    request_posts = BlogPost.query.filter_by(categories_id=cat_id).order_by(desc(BlogPost.id))
    one_category = Categories.query.get(cat_id)
    page = request.args.get('page', 1, type=int)
    pages = request_posts.paginate(page=page, per_page=8)



    return render_template('catposts.html',posts=request_posts,category=one_category,pages=pages)





###################### Blog Functions ##############################

@app.route('/')
def homepage():
    all_cats = Categories.query.all()
    all_activities = Activities.query.all()
    all_activities = all_activities[::-1]
    all_activities = all_activities[0:3]
    return render_template('home.html',cats = all_cats, activities = all_activities)

@app.route('/blog',methods=['GET','POST'])
def get_all_posts():
    posts = BlogPost.query.order_by(desc(BlogPost.id))
    page = request.args.get('page',1,type=int)
    #page = request.args.get(get_page_parameter(), type=int, default=1)
    # if page and page.isdigit():
    #     page = int(page)
    # else:
    #     page = 1
    pages = posts.paginate(page=page,per_page=8)
    #pages = Pagination(page=page,per_page=2)

    return render_template("index.html", all_posts=posts,pages=pages)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )

        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('get_all_posts'))
    return render_template("register.html",form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # Find user by email entered.
        user = User.query.filter_by(email=email).first()

        # Email doesn't exist
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        # Password incorrect
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        # Email exists and password correct
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", logged_in=current_user.is_authenticated,form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['GET','POST'])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.body.data,
            comment_author=current_user,
            parent_post=requested_post
        )

        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post',post_id=post_id))
    return render_template("post.html", post=requested_post,form=form,current_user=current_user)

content_list = ['Hi']


@app.route('/edit-about', methods=['GET', 'POST'])
@admin_only
def editabout():
    form = AboutForm()
    if form.validate_on_submit():
        content = form.body.data
        content_list.append(content)
        return render_template("about.html", content=content)
    return render_template("make-about.html", form=form)


@app.route("/about")
def about():
    content = content_list[len(content_list)-1]
    return render_template("about.html",content=content)




@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=['GET','POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            categories_id = form.category_id.data,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=['GET','POST'])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        categories_id=post.categories_id,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))






if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000,debug=True)
