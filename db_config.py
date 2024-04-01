import psycopg2
from psycopg2 import sql

class DBConfig:
    def __init__(self, dbname, user, password, host, port):
        self.conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        self.cursor = self.conn.cursor()

    def __del__(self):
        self.conn.close()

    def insert_user(self, first_name, last_name, username, email, number, password, balance, language, is_authenticated):
        self.cursor.execute(sql.SQL("INSERT INTO User (first_name, last_name, username, email, number, password, balance, language, is_authenticated) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"),
                            (first_name, last_name, username, email, number, password, balance, language, is_authenticated))
        self.conn.commit()

    def get_products(self):
        self.cursor.execute("SELECT * FROM product")
        return self.cursor.fetchall()

    def update_balance(self, user_id, new_balance):
        self.cursor.execute("UPDATE User SET balance = %s WHERE id = %s", (new_balance, user_id))
        self.conn.commit()

# Example usage
if __name__ == '__main__':
    # Initialize the TelegramBotDB object
    db = TelegramBotDB(
        dbname="your_database",
        user="your_username",
        password="your_password",
        host="your_host",
        port="your_port"
    )

    # Insert a new user
    db.insert_user("John", "Doe", "johndoe", "johndoe@example.com", "123456789", "password123", 1000, "en", 1)

    # Retrieve all products
    products = db.get_products()
    print("Products:")
    for product in products:
        print(product)

    # Update user's balance
    db.update_balance(1, 1500)
