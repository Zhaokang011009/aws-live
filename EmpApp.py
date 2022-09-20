from sqlite3 import Cursor
from flask import Flask, render_template, request
from pymysql import connections
import os
import pathlib
import boto3
from config import *

app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb
)

output = {}
table = 'employee'

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('AddEmp.html')

@app.route("/about")
def about():
    return render_template('AboutUs.html')

@app.route("/getEmp", methods=['POST'])
def getEmp():
    cursor = db_conn.cursor()
    emp_id = request.form['emp_id']
    print(emp_id)
    getEmpSQL = "Select * from employee WHERE emp_id = %s"
    cursor.execute(getEmpSQL, emp_id)
    employee = cursor.fetchone()
    print(employee)

    cursor.close()
    return render_template('GetEmp.html', empData = employee, bucketName = bucket)

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']

    cursor = db_conn.cursor()

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"

    if emp_image_file.filename == "":
        return "Please select a file"

    else:
        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file.png"
        s3 = boto3.resource('s3')

        print("Data inserted in MySQL RDS... uploading image to S3...")
        s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
        s3_location = (bucket_location['LocationConstraint'])

        if s3_location is None:
            s3_location = ''
        else:
            s3_location = '-' + s3_location

        object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
            s3_location,
            custombucket,
            emp_image_file_name_in_s3)

    cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)

@app.route("/updateEmp", methods=['POST'])
def EditEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['emp_first_name']
    last_name = request.form['emp_last_name']
    pri_skill = request.form['emp_pri_skill']
    location = request.form['emp_location']
    emp_image_file = request.files['emp_image_file']

    cursor = db_conn.cursor()
    update_sql = "UPDATE employee SET first_name = %s, last_name = %s, pri_skill = %s, location = %s WHERE emp_id = %s"

    #update data
    cursor.execute(update_sql, (first_name, last_name, pri_skill, location, emp_id))
    db_conn.commit()
    if emp_image_file.filename != "":
        
        # Upload image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file.png"
        s3 = boto3.resource('s3')

        s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
        s3_location = (bucket_location['LocationConstraint'])

        if s3_location is None:
            s3_location = ''
        else:
            s3_location = '-' + s3_location

        object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
            s3_location,
            custombucket,
            emp_image_file_name_in_s3)

    cursor.close()
    return render_template('AddEmp.html')

@app.route("/removeEmp", methods=['POST'])
def RemoveEmp():
    cursor = db_conn.cursor()
    emp_id = request.form['emp_ID']
    print(emp_id)
    remove_sql = "Delete from employee WHERE emp_id = %s"
    emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file.png"

    #remove data
    cursor.execute(remove_sql, emp_id)
    s3 = boto3.resource('s3')
    s3.Object(custombucket, emp_image_file_name_in_s3).delete()
    db_conn.commit()
    cursor.close()

    cursor = db_conn.cursor()
    cursor.execute("Select * from employee")
    employeeList = cursor.fetchall()
    print(employeeList)
    cursor.close()
    return render_template('DisplayEmployee.html', empList = employeeList, bucketName = bucket)

@app.route("/listEmp", methods=['POST'])
def displayEmp():
    cursor = db_conn.cursor()
    cursor.execute("Select * from employee")
    employeeList = cursor.fetchall()
    print(employeeList)
    cursor.close()

    return render_template('DisplayEmployee.html', empList = employeeList, bucketName = bucket)

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=80, debug=True)
