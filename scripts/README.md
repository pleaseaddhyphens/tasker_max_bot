# Только ID участников
```
curl http://localhost:8000/chat/-68973305722340/participants
```

# Полная информация об участниках
```
curl http://localhost:8000/chat/-68973305722340/members
```
# Для чата по умолчанию
```
curl http://localhost:8000/chat/default/participants
```
```
curl http://localhost:8000/chat/default/members
```
# Только администраторы
```
curl http://localhost:8000/chat/-68973305722340/members/admins
```
# Только боты
```
curl http://localhost:8000/chat/-68973305722340/members/bots
```