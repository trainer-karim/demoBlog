from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import boto3
import os
import pymysql
from botocore.exceptions import ClientError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://admin:admin123*@blogdb.c4zwod0hvwjn.us-east-1.rds.amazonaws.com/blogdb'

db = SQLAlchemy(app)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)

@app.route('/add', methods=['POST'])
def add():
    title = request.form['title']
    content = request.form['content']
    file = request.files['image']

    s3_resource = boto3.resource('s3')
    s3_resource.Bucket('your-bucket-name').put_object(Key=file.filename, Body=file)
    image_url = f"https://demoblog-store.s3.amazonaws.com/{file.filename}"

    post = BlogPost(title=title, content=content, image_url=image_url)
    db.session.add(post)
    db.session.commit()

    return 'Done'

if __name__ == '__main__':
    # Get RDS details from environment variables
    rds_host = os.environ['RDS_HOST']
    rds_user = os.environ['RDS_USER']
    rds_password = os.environ['RDS_PASSWORD']
    rds_db = os.environ['RDS_DB']

    # Connect to RDS
    conn = pymysql.connect(rds_host, user=rds_user, passwd=rds_password, db=rds_db, connect_timeout=5)

    # Check if table exists
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES LIKE 'BlogPost';")
        result = cur.fetchone()

    # If table doesn't exist, invoke CreateTable Lambda function
    if not result:
        lambda_client = boto3.client('lambda')
        try:
            response = lambda_client.invoke(
                FunctionName='CreateTable',
                InvocationType='RequestResponse'
            )
            print('Table created successfully!')
        except ClientError as e:
            print(f'Failed to create table: {e}')

    @app.route('/')
    def home():
        posts = BlogPost.query.all()
        return render_template('home.html', posts=posts)

    # Run the Flask application after the DB and table verification and setup
    app.run(debug=True, host='0.0.0.0')
