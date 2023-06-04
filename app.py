from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import boto3
import os
from datetime import datetime
import pymysql
pymysql.install_as_MySQLdb()  # Add this line
from botocore.exceptions import ClientError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://admin:admin123*@blogdb.c4zwod0hvwjn.us-east-1.rds.amazonaws.com/blogdb'
app.config['UPLOAD_FOLDER'] = '/home/ec2-user/demoBlog'
db = SQLAlchemy(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    publish_at = db.Column(db.DateTime, nullable=True)
    published = db.Column(db.Boolean, default=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            #s3 = boto3.client('s3',
            #    aws_access_key_id='your-access-key',
            #    aws_secret_access_key='your-secret-key'
            #)
            s3.upload_fileobj(image, 'demoblog-store', filename)
            image_url = f"https://demoblog-store.s3.amazonaws.com/{filename}"
        else:
            image_url = None

        publish_at = request.form.get('publish_at')
        if publish_at:
            publish_at = datetime.strptime(publish_at, "%Y-%m-%d %H:%M")

        post = Post(title=title, content=content, image_url=image_url, publish_at=publish_at)
        db.session.add(post)
        db.session.commit()

        return 'Post created.'

    posts = Post.query.filter(Post.publish_at <= datetime.now(), Post.published == True).all()
    for post in posts:
        if post.image_url:
            # Parse the bucket name and key from the image_url
            bucket_name = 'demoblog-store'  # replace with your bucket name
            key = post.image_url.split(f"https://{bucket_name}.s3.amazonaws.com/")[1]

            # Generate a presigned URL for the S3 object
            post.image_url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': key})
    
    return render_template('index.html', posts=posts)






def create_table_if_not_exists():
    # Get RDS details from environment variables
    rds_host = os.environ['RDS_HOST']
    rds_user = os.environ['RDS_USER']
    rds_password = os.environ['RDS_PASSWORD']
    rds_db = os.environ['RDS_DB']

    # Connect to RDS
    conn = pymysql.connect(host=rds_host, user=rds_user, passwd=rds_password, db=rds_db, connect_timeout=5)

    # Check if table exists
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES LIKE 'blog_post';")
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

if __name__ == '__main__':
    create_table_if_not_exists()
    app.run(debug=True, host='0.0.0.0')
