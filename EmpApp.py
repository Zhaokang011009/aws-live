from sqlite3 import Cursor
from flask import Flask, redirect, url_for, render_template, request
from pymysql import connections
from datetime import date
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

#navigation function

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('Home.html')

@app.route("/about", methods=['POST'])
def about():
    return render_template('AboutUs.html')

@app.route("/goAdd", methods=['POST'])
def goAdd():
    return render_template('AddEmp.html')

@app.route("/goUploadDoc", methods=['POST'])
def uploadFilePage():
    return render_template('UploadDoc.html')

@app.route("/goAddLeave", methods=['POST'])
def addLeavePage(): 
    return render_template('ApplyLeave.html')

@app.route("/goRegisterTraining", methods=['POST'])
def addTrainingPage():
    return render_template('AddTraining.html')

@app.route("/listEmp", methods=['POST'])
def displayEmp():
    cursor = db_conn.cursor()
    cursor.execute("Select * from employee")
    employeeList = cursor.fetchall()
    print(employeeList)
    cursor.close()

    return render_template('DisplayEmployee.html', empList = employeeList, bucketName = bucket)

@app.route("/listDoc", methods=['POST'])
def displayDoc():
    cursor = db_conn.cursor()
    select_doc_sql = "Select d.doc_url, e.first_name, e.last_name FROM employee as e, document as d WHERE e.emp_id = d.link_emp_id"
    cursor.execute(select_doc_sql)
    documentList = cursor.fetchall()
    print(documentList)
    cursor.close()

    return render_template('DisplayDocument.html', documentList = documentList)

@app.route("/listLeave", methods=['POST'])
def displayLeave(): 
    cursor = db_conn.cursor()
    select_leave_sql = "SELECT l.from_date, l.to_date, e.first_name, e.last_name, l.reason_apply, l.approved_date FROM leaveEmployee AS l, employee AS e WHERE l.link_emp_id = e.emp_id"
    cursor.execute(select_leave_sql)
    leaveList = cursor.fetchall()
    cursor.close()
    return render_template('DisplayLeave.html', leaveList = leaveList)

@app.route("/listTraining", methods=['POST'])
def displayTraining():
    cursor = db_conn.cursor()
    select_t_sql = "Select t.t_id, t.t_name, t.t_date, t.t_time, e.first_name, e.last_name FROM employee as e, trainingClass as t WHERE e.emp_id = t.t_emp_id"
    cursor.execute(select_t_sql)
    trainingList = cursor.fetchall()
    print(trainingList)
    cursor.close()

    return render_template('DisplayTraining.html', trainingList = trainingList)

#CRUD employee function

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

@app.route("/getEmp", methods=['POST'])
def getEmp():
    cursor = db_conn.cursor()
    emp_id_get = request.form['emp_IDs']
    print(emp_id_get)
    getEmpSQL = "Select * from employee WHERE emp_id = %s"
    cursor.execute(getEmpSQL, emp_id_get)
    employee = cursor.fetchone()
    cursor.close()

    cursor = db_conn.cursor()
    getEmpDocSQL = "Select * from document WHERE link_emp_id = %s"
    cursor.execute(getEmpDocSQL, emp_id_get)
    docList = cursor.fetchall()
    cursor.close()

    return render_template('GetEmp.html', empData = employee, bucketName = bucket, docList = docList)

@app.route("/searchEmp", methods=['POST'])
def searchEmp():
    emp_search_name = request.form['emp_name']
    search_emp_sql = "SELECT * FROM employee WHERE first_name = %s OR last_name = %s"
    cursor = db_conn.cursor()
    cursor.execute(search_emp_sql, (emp_search_name, emp_search_name))
    employeeList = cursor.fetchall()
    cursor.close()

    return render_template('DisplayEmployee.html', empList = employeeList, bucketName = bucket)


@app.route("/updateEmp", methods=['POST'])
def EditEmp():
    emp_id_edt = request.form['employeeID']
    first_name_edt = request.form['emp_first_name']
    last_name_edt = request.form['emp_last_name']
    pri_skill_edt = request.form['emp_pri_skill']
    location_edt = request.form['emp_location']
    emp_image_file_edt = request.files['emp_image_file']

    cursor = db_conn.cursor()
    update_sql = "UPDATE employee SET first_name = %s, last_name = %s, pri_skill = %s, location = %s WHERE emp_id = %s"

    #update data
    cursor.execute(update_sql, (first_name_edt, last_name_edt, pri_skill_edt, location_edt, emp_id_edt))
    db_conn.commit()
    if emp_image_file_edt.filename != "":
        
        # Upload image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id_edt) + "_image_file.png"
        s3 = boto3.resource('s3')

        s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file_edt)
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
    emp_id = request.form['emp_IDs']
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

#file function

@app.route("/uploadDoc", methods=['POST'])
def uploadFile():
    emp_id_to_upload = request.form['uploadEmp']
    important_file = request.files['uploadDocInput']

    doc_to_upload_s3 = "emp_" + emp_id_to_upload + "_" + important_file.filename
    doc_insert_sql = "INSERT INTO document VALUES (%s, %s, %s)"
    doc_count_sql = "SELECT COUNT(doc_id)+1 FROM document"

    #get count
    cursor = db_conn.cursor()
    cursor.execute(doc_count_sql)
    totalCountDoc = cursor.fetchone()
    cursor.close()

    doc_id_str = "D" + str(totalCountDoc[0])
    cursor = db_conn.cursor()

    if important_file == "":
        return "Please choose a document"
    else: 
        cursor.execute(doc_insert_sql, (doc_id_str, doc_to_upload_s3, emp_id_to_upload))
        db_conn.commit()
        # Uplaod image file in S3 #
        s3 = boto3.resource('s3')

        s3.Bucket(custombucket).put_object(Key=doc_to_upload_s3, Body=important_file)
        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
        s3_location = (bucket_location['LocationConstraint'])

        if s3_location is None:
            s3_location = ''
        else:
            s3_location = '-' + s3_location

        object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
            s3_location,
            custombucket,
            doc_to_upload_s3)

    cursor.close()
    return render_template('Home.html')

@app.route("/removeDoc", methods=['POST'])
def removeDoc():
    cursor = db_conn.cursor()
    remove_doc_name = request.form['removeDocument']
    remove_sql = "Delete from document WHERE doc_url = %s"

    #remove data
    cursor.execute(remove_sql, remove_doc_name)
    s3 = boto3.resource('s3')
    s3.Object(custombucket, remove_doc_name).delete()
    db_conn.commit()
    cursor.close()

    cursor = db_conn.cursor()
    cursor.execute("Select * from employee")
    employeeList = cursor.fetchall()
    cursor.close()
    return render_template('DisplayEmployee.html', empList = employeeList, bucketName = bucket)

#leave function
@app.route("/addLeave", methods=['POST'])
def addLeave():
    emp_id_leave = request.form['emp_id_leave']
    leave_from_date = request.form['leave_from_date']
    leave_to_date = request.form['leave_to_date']
    reason_apply = request.form['reason_apply']

    add_leave_sql = "INSERT INTO leaveEmployee VALUES (%s, %s, %s, %s, %s, %s)"
    count_leave_sql = "SELECT COUNT(leave_id)+1 FROM leaveEmployee"

    cursor = db_conn.cursor()
    cursor.execute(count_leave_sql)
    totalCountLeave = cursor.fetchone()

    leave_id = "L" + str(totalCountLeave[0])

    cursor.execute(add_leave_sql, (leave_id, str(date.today()), str(leave_from_date), str(leave_to_date), reason_apply, emp_id_leave))
    db_conn.commit()
    cursor.close()
    return render_template('Home.html')

#training function
@app.route("/addTraining", methods=['POST'])
def addTraining():
    empID = request.form['T_emp_ID']
    trainClass = request.form['T_name']
    date = request.form['T_date']
    time = request.form['T_time']

    T_insert_sql = "INSERT INTO trainingClass VALUES (%s, %s, %s, %s, %s)"
    T_count_sql = "SELECT COUNT(t_id)+1 FROM trainingClass"

    #get count
    cursor = db_conn.cursor()
    cursor.execute(T_count_sql)
    totalCountClass = cursor.fetchone()
    cursor.close()

    T_id_str = "T" + str(totalCountClass[0])
    cursor = db_conn.cursor()

    if empID == "":
        return "Please Enter Employee ID"
    elif date =="":
         return "Please Enter Date"
    elif time =="":
        return "Please Enter Time"
    else: 
        cursor.execute(T_insert_sql, (T_id_str, trainClass, date, time, empID))
        db_conn.commit()


    cursor.close()
    return render_template('Home.html')

@app.route("/removeTraining", methods=['POST'])
def removeTraining():
    cursor = db_conn.cursor()
    id = request.form['t_id']
    remove_sql = "Delete from trainingClass WHERE t_id = %s"

    #remove data
    cursor.execute(remove_sql, id)
    db_conn.commit()
    cursor.close()

    cursor = db_conn.cursor()
    select_t_sql = "Select t.t_id, t.t_name, t.t_date, t.t_time, e.first_name, e.last_name FROM employee as e, trainingClass as t WHERE e.emp_id = t.t_emp_id"
    cursor.execute(select_t_sql)
    trainingList = cursor.fetchall()
    print(trainingList)
    cursor.close()

    return render_template('DisplayTraining.html', trainingList = trainingList)

@app.route("/filterTraining", methods=['POST'])
def filterTraining():
    cursor = db_conn.cursor()
    dateToday = date.today()
    select_t_sql = "Select t.t_id, t.t_name, t.t_date, t.t_time, e.first_name, e.last_name FROM employee as e, trainingClass as t WHERE e.emp_id = t.t_emp_id AND t.t_date = %s"
    cursor.execute(select_t_sql, dateToday)
    trainingList = cursor.fetchall()
    print(trainingList)
    cursor.close()

    return render_template('DisplayTraining.html', trainingList = trainingList)

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=80, debug=True)
