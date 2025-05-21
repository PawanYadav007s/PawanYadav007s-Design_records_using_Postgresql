status=input()

if(status=="pending"):
    print("Pending")
elif(status=="approved"):
    print("Approved")
elif(status=="rejected"):
    print("Rejected")
elif(status=="completed"):
    print("Completed")
elif(status=="in progress"):
    print("In Progress")
elif(status=="on hold"):
    print("On Hold")
elif(status=="canceled"):
    print("Canceled")
elif(status=="delayed"):
    print("Delayed")
elif(status=="not started"):
    print("Not Started")
elif(status=="in review"):
    print("In Review")
else:
    print("Unknown Status")
    