from pydoc import doc
from sqlite3 import Cursor
from typing_extensions import Self
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

def create_connection():
    return connections.Connection(
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
    db_conn = create_connection()

    emp_count_sql = "SELECT COUNT(emp_id) FROM employee"
    doc_count_sql = "SELECT COUNT(doc_id) FROM document"
    leave_count_sql = "SELECT COUNT(leave_id) FROM leaveEmployee"
    training_count_sql = "SELECT COUNT(t_id) FROM trainingClass"

    db_conn.ping(reconnect = True)
    cursor = db_conn.cursor()
    cursor.execute(emp_count_sql)
    empCount = cursor.fetchone()
    cursor.execute(doc_count_sql)
    docCount = cursor.fetchone()
    cursor.execute(leave_count_sql)
    leaveCount = cursor.fetchone()
    cursor.execute(training_count_sql)
    trainingCount = cursor.fetchone()
    cursor.close()

    return render_template('Home.html', empCount = empCount, docCount = docCount, leaveCount = leaveCount, trainingCount = trainingCount)

@app.route("/about", methods=['POST'])
def about():
    return render_template('AboutUs.html')

@app.route("/goAdd", methods=['POST'])
def goAddEmpPage():
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
    db_conn = create_connection()
    cursor = db_conn.cursor()
    cursor.execute("Select * from employee")
    employeeList = cursor.fetchall()
    print(employeeList)
    cursor.close()

    return render_template('DisplayEmployee.html', empList = employeeList, bucketName = bucket)

@app.route("/listDoc", methods=['POST'])
def displayDoc():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    select_doc_sql = "Select d.doc_url, e.first_name, e.last_name FROM employee as e, document as d WHERE e.emp_id = d.link_emp_id"
    cursor.execute(select_doc_sql)
    documentList = cursor.fetchall()
    cursor.close()

    return render_template('DisplayDocument.html', documentList = documentList)

@app.route("/listLeave", methods=['POST'])
def displayLeave(): 
    db_conn = create_connection()
    cursor = db_conn.cursor()
    select_leave_sql = "SELECT l.leave_id, l.from_date, l.to_date, e.first_name, e.last_name, l.reason_apply, l.approved_date FROM leaveEmployee AS l, employee AS e WHERE l.link_emp_id = e.emp_id"
    cursor.execute(select_leave_sql)
    leaveList = cursor.fetchall()
    cursor.close()
    return render_template('DisplayLeave.html', leaveList = leaveList)

@app.route("/listTraining", methods=['POST'])
def displayTraining():
    db_conn = create_connection()
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

    db_conn = create_connection()
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
    
    getEmpSQL = "Select * from employee WHERE emp_id = %s"
    cursor.execute(getEmpSQL, emp_id)
    newEmployee = cursor.fetchone()
    cursor.close()

    

    print("all modification done...")
    return render_template('AddEmpSuccessful.html', bucketName = bucket, empData = newEmployee)

@app.route("/edtEmp", methods=['POST'])
def edtEmp():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    emp_id_get = request.form['emp_IDs']
    getEmpSQL = "Select * from employee WHERE emp_id = %s"
    cursor.execute(getEmpSQL, emp_id_get)
    employee = cursor.fetchone()
    cursor.close()

    cursor = db_conn.cursor()
    getEmpDocSQL = "Select * from document WHERE link_emp_id = %s"
    cursor.execute(getEmpDocSQL, emp_id_get)
    docList = cursor.fetchall()
    cursor.close()

    return render_template('EditEmp.html', empData = employee, bucketName = bucket, docList = docList)

@app.route("/searchEmp", methods=['POST'])
def searchEmp():
    db_conn = create_connection()
    emp_search = request.form['emp_name']
    search_emp_sql = "SELECT * FROM employee WHERE first_name = %s OR last_name = %s OR pri_skill = %s OR location = %s"
    cursor = db_conn.cursor()
    cursor.execute(search_emp_sql, (emp_search, emp_search, emp_search, emp_search))
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

    db_conn = create_connection()
    cursor = db_conn.cursor()
    update_sql = "UPDATE employee SET first_name = %s, last_name = %s, pri_skill = %s, location = %s WHERE emp_id = %s"
    select_editEmp_sql = "Select * FROM employee WHERE emp_id = %s"

    #update data
    if emp_image_file_edt.filename == "":
        return "Please select a file"

    else:
        cursor.execute(update_sql, (first_name_edt, last_name_edt, pri_skill_edt, location_edt, emp_id_edt))
        db_conn.commit()
        # Upload image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id_edt) + "_image_file.png"
        s3 = boto3.resource('s3')

        print("Data inserted in MySQL RDS... uploading image to S3...")
        s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file_edt)
        bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
        s3_location = (bucket_location['LocationConstraint'])

        if s3_location is None:
            s3_location = ''
        else:
            s3_location = '-' + s3_location

    cursor.execute(select_editEmp_sql, emp_id_edt)
    empEditData = cursor.fetchone()

    cursor = db_conn.cursor()
    getEmpDocSQL = "Select * from document WHERE link_emp_id = %s"
    cursor.execute(getEmpDocSQL, emp_id_edt)
    docList = cursor.fetchall()

    cursor.close()
    return render_template('EditEmpSuccessful.html', empData = empEditData, bucketName = bucket, docList = docList)

@app.route("/removeEmp", methods=['POST'])
def RemoveEmp():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    emp_id = request.form['emp_IDs']
    print(emp_id)
    remove_sql = "Delete from employee WHERE emp_id = %s"
    select_nameDeleteEmp_sql = "Select first_name, last_name from employee WHERE emp_id = %s"
    emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file.png"

    #select name first
    cursor.execute(select_nameDeleteEmp_sql, emp_id)
    emp_deleted_name = cursor.fetchone()

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
    return render_template('RemoveEmpSuccessful.html', bucketName = bucket, deletedName = emp_deleted_name)

#file function

@app.route("/uploadDoc", methods=['POST'])
def uploadFile():
    emp_id_to_upload = request.form['uploadEmp']
    important_file = request.files['uploadDocInput']

    doc_to_upload_s3 = "emp_" + emp_id_to_upload + "_" + important_file.filename
    doc_insert_sql = "INSERT INTO document VALUES (%s, %s, %s)"
    emp_name_doc_sql = "Select first_name, last_name from employee WHERE emp_id = %s"
    doc_count_sql = "SELECT COUNT(doc_id)+1 FROM document"

    #get count
    db_conn = create_connection()
    cursor = db_conn.cursor()
    cursor.execute(doc_count_sql)
    totalCountDoc = cursor.fetchone()

    doc_id_str = "D" + str(totalCountDoc[0])

    #get emp name
    cursor.execute(emp_name_doc_sql, emp_id_to_upload)
    emp_name_belonging = cursor.fetchone()

    #upload file

    if important_file == "":
        return "Please choose a document"
    else: 
        cursor.execute(doc_insert_sql, (doc_id_str, doc_to_upload_s3, emp_id_to_upload))
        db_conn.commit()
        # Uplaod file in S3 #
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
    return render_template('UploadDocSuccessful.html', docName = important_file.filename, empName = emp_name_belonging)

@app.route("/removeDoc", methods=['POST'])
def removeDoc():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    remove_doc_name = request.form['removeDocument']
    remove_sql = "Delete from document WHERE doc_url = %s"
    select_remove_doc_sql = "SELECT e.first_name, e.last_name FROM document d, employee e WHERE d.link_emp_id = e.emp_id AND d.doc_url = %s"

    cursor.execute(select_remove_doc_sql, remove_doc_name)
    empName = cursor.fetchone()

    #remove data
    cursor.execute(remove_sql, remove_doc_name)
    s3 = boto3.resource('s3')
    s3.Object(custombucket, remove_doc_name).delete()
    db_conn.commit()
    cursor.close()

    return render_template('RemoveDocSuccessful.html', empName = empName, bucketName = bucket, removedDocName = remove_doc_name)

@app.route("/searchDoc", methods=['POST'])
def searchDoc():
    db_conn = create_connection()
    doc_search = request.form['doc_name']
    search_doc_sql = "SELECT d.doc_url, e.first_name, e.last_name FROM employee as e, document as d WHERE (d.doc_url = %s OR e.first_name = %s OR e.last_name = %s) AND (e.emp_id = d.link_emp_id)"
    cursor = db_conn.cursor()
    cursor.execute(search_doc_sql, (doc_search, doc_search, doc_search))
    documentList = cursor.fetchall()
    cursor.close()

    return render_template('DisplayDocument.html', documentList = documentList, bucketName = bucket)

#leave function
@app.route("/addLeave", methods=['POST'])
def addLeave():
    emp_id_leave = request.form['emp_id_leave']
    leave_from_date = request.form['leave_from_date']
    leave_to_date = request.form['leave_to_date']
    reason_apply = request.form['reason_apply']

    add_leave_sql = "INSERT INTO leaveEmployee VALUES (%s, %s, %s, %s, %s, %s)"
    emp_name_leave_sql = "Select first_name, last_name from employee WHERE emp_id = %s"
    count_leave_sql = "SELECT COUNT(leave_id)+1 FROM leaveEmployee"

    db_conn = create_connection()
    cursor = db_conn.cursor()

    cursor.execute(emp_name_leave_sql, emp_id_leave)
    empName = cursor.fetchone()

    cursor.execute(count_leave_sql)
    totalCountLeave = cursor.fetchone()

    leave_id = "L" + str(totalCountLeave[0])

    cursor.execute(add_leave_sql, (leave_id, str(date.today()), str(leave_from_date), str(leave_to_date), reason_apply, emp_id_leave))
    db_conn.commit()
    cursor.close()
    return render_template('ApplyLeaveSuccessful.html', empName = empName)

@app.route("/removeLeave", methods=['POST'])
def removeLeave():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    leave_id = request.form['removeLeaveID']
    remove_sql = "Delete from leaveEmployee WHERE leave_id = %s"
    select_leave_name_sql = "Select e.first_name, e.last_name from employee as e, leaveEmployee as le WHERE le.link_emp_id = e.emp_id AND leave_id = %s"

    cursor.execute(select_leave_name_sql, leave_id)
    leave_name = cursor.fetchone()

    #remove data
    cursor.execute(remove_sql, leave_id)
    db_conn.commit()
    cursor.close()

    return render_template('RemoveLeaveSuccessful.html', leave_name = leave_name)

@app.route("/searchLeave", methods=['POST'])
def searchLeave():
    db_conn = create_connection()
    leave_search = request.form['leave_name']
    search_leave_sql = "SELECT l.leave_id, l.from_date, l.to_date, e.first_name, e.last_name, l.reason_apply, l.approved_date FROM leaveEmployee AS l, employee AS e WHERE (l.from_date = %s OR l.to_date = %s OR e.first_name = %s OR e.last_name = %s OR l.reason_apply = %s OR l.approved_date = %s) AND (l.link_emp_id = e.emp_id)"
    cursor = db_conn.cursor()
    cursor.execute(search_leave_sql, (leave_search, leave_search, leave_search, leave_search, leave_search, leave_search))
    leaveList = cursor.fetchall()
    cursor.close()

    return render_template('DisplayLeave.html', leaveList = leaveList, bucketName = bucket)

#training function
@app.route("/addTraining", methods=['POST'])
def addTraining():
    empID = request.form['T_emp_ID']
    trainClass = request.form['T_name']
    date = request.form['T_date']
    time = request.form['T_time']

    T_insert_sql = "INSERT INTO trainingClass VALUES (%s, %s, %s, %s, %s)"
    T_count_sql = "SELECT COUNT(t_id)+1 FROM trainingClass"
    emp_name_training_sql = "Select first_name, last_name from employee WHERE emp_id = %s"

    db_conn = create_connection()
    cursor = db_conn.cursor()
    cursor.execute(emp_name_training_sql, empID)
    empName = cursor.fetchone()

    #get count
    cursor.execute(T_count_sql)
    totalCountClass = cursor.fetchone()

    T_id_str = "T" + str(totalCountClass[0])

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
    return render_template('AddTrainingSuccessful.html', empName = empName)

@app.route("/removeTraining", methods=['POST'])
def removeTraining():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    removeTrainingID = request.form['t_id']
    remove_sql = "Delete from trainingClass WHERE t_id = %s"
    emp_name_training_sql = "Select e.first_name, e.last_name from trainingClass as t, employee as e WHERE t.t_id = %s AND e.emp_id = t.t_emp_id"

    cursor.execute(emp_name_training_sql, removeTrainingID)
    empName = cursor.fetchone()

    #remove data
    cursor.execute(remove_sql, removeTrainingID)
    db_conn.commit()
    cursor.close()

    return render_template('RemoveTrainingSuccessful.html', empName = empName)

@app.route("/searchTraining", methods=['POST'])
def searchTraining():
    db_conn = create_connection()
    cursor = db_conn.cursor()
    training_search = request.form['training_name']
    select_t_sql = "Select t.t_id, t.t_name, t.t_date, t.t_time, e.first_name, e.last_name FROM employee as e, trainingClass as t WHERE (t.t_id = %s OR t.t_name = %s OR t.t_date = %s OR t.t_time = %s OR e.first_name = %s OR e.last_name = %s) AND (e.emp_id = t.t_emp_id)"
    cursor.execute(select_t_sql, (training_search, training_search, training_search, training_search, training_search, training_search))
    trainingList = cursor.fetchall()
    print(trainingList)
    cursor.close()

    return render_template('DisplayTraining.html', trainingList = trainingList)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
