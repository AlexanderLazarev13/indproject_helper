# Техническая документация #
- ## Библиотеки: ##
  - aiogram
  - asyncio
  - sqlite3
  - datetime
  - random
- ## Используемые инструменты/материалы: ##
  - pycharm
  - google coloboratory
  - geeksforgeeks.org
  - Telegram
- ## Базы данных, созданные для проекта: ##
  - *users*:
    - user_id (ID пользователя в Telegram)
    - role (ученик/учитель)
    - first_name (фамилия)
    - last_name(имя)
    - middle_name(отчество для учителей)
    - grade (номер класса)
    - username (ник пользователя в Telegram)
    - project_topic (тема проекта ученика)
    - password (пароль учителя)
    - curator_id (ID куратора для ученика)
    - curator_request_status (статус задания; по умолчанию 'pending')
  - *tasks*:
    - id (номер задания в базе данных)
    - student_id (ID ученика)
    - teacher_id (ID куратора)
    - task_text (описание задания)
    - deadline (дедлайн выполнения)
    - status (статус в выполнении задания)
    - media_id (файл фото/видео)
    - media_type (фото/видео)
  - ## Состояния FSM в виде классов: ##
    - Registration:
      - choosing_role (роль)
      - student_name/teacher_name (имя ученика/учителя)
      - student_class + student_project_topic / teacher password (класс + тема проекта / пароль)
    - CuratorRequest:
      - teacher_fio (ФИО учителя)
      - teacher_password (пароль)
    - TaskAssignment:
      - task_text (описание задания)
      - task_deadline (дедлайн)
    - DeleteAccount:
      - confirm_code (код подтверждения)
