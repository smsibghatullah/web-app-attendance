import requests
import json
 
url = "http://170.64.233.41:8090/api1/auth/token"
 
payload = json.dumps({
  "db": "New_UAT",
  "login": "sibghatullah@gmail.com",
  "password": "1234"
})
headers = {
  'Content-Type': 'application/json',
  'Cookie': 'session_id=a5e4e63c54fdbbe63f68146e477202621de2c5b3'
}
 
response = requests.request("POST", url, headers=headers, data=payload)
 
print(response.text)
 