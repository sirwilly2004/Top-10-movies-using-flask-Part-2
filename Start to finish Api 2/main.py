from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, FloatField
from wtforms.validators import DataRequired
import requests
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6dWlSihBXox7C0sKR6b'
Bootstrap(app)

# loading env and api keys
load_dotenv()
API_KEY = os.getenv('API_KEY')

# protection 
csrf = CSRFProtect(app)

# instantiate the database
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///movies.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# creating database with sqlalchemy
class Movies(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    reviews = db.Column(db.String(150), nullable=True)
    img_url = db.Column(db.String(150), nullable=False)
    ranking = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"Movie('{self.title}', '{self.year}', '{self.rating}')"

class DeleteForm(FlaskForm):
    submit = SubmitField('Delete')
# FlaskForm for adding movies
class MovieForm(FlaskForm):
    title = StringField(label='Movie Title', validators=[DataRequired()])
    year = IntegerField(label='Year', validators=[DataRequired()])
    description = StringField(label='Description', validators=[DataRequired()])
    rating = FloatField(label='Rating', validators=[DataRequired()])
    reviews = StringField(label='Reviews', validators=[DataRequired()])
    img_url = StringField(label='Image URL', validators=[DataRequired()])
    ranking = IntegerField(label='Ranking', validators=[DataRequired()])
    submit = SubmitField(label='Add Movie')

class RateMovieForm(FlaskForm):
    reviews = StringField(label='Your Review', validators=[DataRequired()])
    rating = FloatField(label='Your Rating Out of 10 e.g. 7.5', validators=[DataRequired()])
    submit = SubmitField(label='Submit')

# FlaskForm for searching movies
class FindMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")

with app.app_context():
    db.create_all()
    
@app.route('/add/manually', methods=['GET', 'POST'])
def add_movies():
    form = MovieForm()
    if form.validate_on_submit():
        new_movie = Movies(
            title=form.title.data,
            year=form.year.data,
            description=form.description.data,
            rating=form.rating.data,
            ranking=form.ranking.data,
            reviews=form.reviews.data,
            img_url=form.img_url.data
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add.html', form=form)


@app.route("/")
def home():
    # This line creates a list of all the movies sorted by rating in descending order
    all_movies = Movies.query.order_by(Movies.rating.desc()).all()
    # This line loops through all the movies
    # for i in range(len(all_movies)):
        # This line gives each movie a new ranking reversed from their order in all_movies
        # all_movies[i].ranking = len(all_movies) - i
    # Commit the changes to the database
    db.session.commit()
    # Render the template with the ranked movies
    return render_template("index.html", movies=all_movies)


@app.route('/update/<int:movie_id>', methods=['POST','GET'])
def update_rate_review(movie_id):
    form = RateMovieForm()
    movie = Movies.query.get_or_404(movie_id)
    if request.method == 'GET':
        # this code help to show the former writing so that the person using the page can be able to remove the one and add another one to it
        # 10=rating
        # i love this = reviews 
        form.rating.data = movie.rating
        form.reviews.data = movie.reviews
    
    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.reviews = form.reviews.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit.html', form=form, movie=movie)

@app.route('/delete/<int:movie_id>', methods=['POST', 'GET'])
def delete_movie(movie_id):
    movie = Movies.query.get_or_404(movie_id)
    form = DeleteForm()
    if request.method == 'POST':
        # If the request is POST, delete the movie
        db.session.delete(movie)
        db.session.commit()
        return redirect(url_for('home'))
    # If the request is GET, show the confirmation page
    return render_template('delete.html', movie=movie, form=form)

# this is the main requirement route with add_one2.html 
@app.route("/add", methods=["GET", "POST"])
def add_movie_api():
    form_one = FindMovieForm()
    if form_one.validate_on_submit():
        movie_title = form_one.title.data
        # Fetch movie details from the OMDb API (or another movie API)

        url_endpoint = f"https://api.themoviedb.org/3/search/movie"
        params ={
            'api_key': API_KEY,
             'query': movie_title
        }
        response = requests.get(url_endpoint, params=params)
        print(response.status_code)
        data = response.json()['results']
        # print(data)
        return render_template('select.html', options=data)
    return render_template('add_one2.html', form=form_one)

@app.route("/movie/<int:movie_id>", methods=['GET','POST'])
def movie_details(movie_id):
    # Fetch detailed movie information using the movie ID
    url_endpoint = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        'api_key': API_KEY
    }
    response = requests.get(url_endpoint, params=params)
    data = response.json()

    if response.status_code == 200:
        title = data['title']
        description  = data.get('overview', 'No description available.')
        year = data.get('release_date', '').split("-")[0]
        
        img_url = None
        if data.get('poster_path'):
            img_url = f"https://image.tmdb.org/t/p/w500{data['poster_path']}"
        
        # Provide default values if rating or reviews are not available
        rating = data.get('vote_average', 0.0)  # Default rating to 0.0
        reviews = data.get('tagline', '')  # Default reviews to an empty string
        ranking = None  # Can be set later in the app logic if required
        
        # Check if the movie already exists in the database
        movie = Movies.query.filter_by(title=title, year=int(year)).first()

        if movie:
            # Movie already exists, redirect to home
            return redirect(url_for('home'))
        else:
            # Add the new movie to the database
            new_movie = Movies(
                title=title,
                year=int(year),
                description=description,
                rating=rating,
                reviews=reviews,
                img_url=img_url,
                ranking=ranking or 0  # Set default ranking to 0
            )
            db.session.add(new_movie)
            db.session.commit()
            return redirect(url_for('home'))
    else:
        # Handle errors from the API call
        return f"Error fetching movie details: {response.status_code}", 500

    
if __name__ == '__main__':
    app.run(debug=True)
