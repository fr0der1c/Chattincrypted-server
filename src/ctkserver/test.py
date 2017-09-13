import json

lst = ['test']
lst_dumps = json.dumps(lst)

u = json.dumps(json.loads(lst_dumps).remove('test'))
print(u)
load2=json.loads(u)
print(load2)