
Table family {
  id int [pk, increment]
  name varchar
  created_at datetime
}

Table parent {
  id int [pk, increment]
  family_id int [ref: > family.id]
  email varchar
  password_hash varchar
  is_head boolean
  created_at datetime
}

Table kid {
  id int [pk, increment]
  family_id int [ref: > family.id]
  name varchar
  pin_code varchar
  coin_balance int
  created_at datetime
}

Table chore {
  id int [pk, increment]
  family_id int [ref: > family.id]
  name varchar
  coin_value int
  point_value int
  created_by_parent_id int [ref: > parent.id]
  created_at datetime
}

Table chore_assignment {
  id int [pk, increment]
  chore_id int [ref: > chore.id]
  kid_id int [ref: > kid.id]
  status varchar // pending, completed, confirmed, rejected
  completed_at datetime
  confirmed_by_parent_id int [ref: > parent.id]
  coin_awarded int
  created_at datetime
}
