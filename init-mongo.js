db = db.getSiblingDB('admin');
db.createUser({
  user: "root",
  pwd: "password",
  roles: [
    { role: "root", db: "admin" },
    { role: "readWriteAnyDatabase", db: "admin" }
  ]
});

// Создание новой базы данных и пользователя для нее
db = db.getSiblingDB('mydatabase'); // Замените mydatabase на нужное название БД
db.createUser({
  user: "mydbuser",
  pwd: "mydbpass",
  roles: [{ role: "readWrite", db: "mydatabase" }]
});
