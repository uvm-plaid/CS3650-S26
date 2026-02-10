from Auth import Auth

auth = Auth("auth_info.json")

user_csv = open("student_info.csv", "r")
user_csv.readline()

for line in user_csv:
    split = line.split(",")
    username = split[2][1:-1]
    password = username[::-1]
    auth.create_user(username, password)
