INSERT INTO auth_permission (name, content_type_id, codename) VALUES (
  'Can enable or disable schedules',
        (select id from django_content_type where model = 'organization'),
'can_enable_disable_schedule'
);


INSERT INTO auth_group_permissions (group_id, permission_id) VALUES (
    (select id from auth_group where name = 'admin'),
    (select id from auth_permission where codename = 'can_enable_disable_schedule')
);


INSERT INTO auth_group_permissions (group_id, permission_id) VALUES (
    (select id from auth_group where name = 'redteam'),
    (select id from auth_permission where codename = 'can_enable_disable_schedule')
);
