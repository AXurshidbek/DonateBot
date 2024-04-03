import psycopg2

class DBConfig():
    def __init__(self):
        # Database configuration (replace with your details)
        self.HOST = "localhost"
        self.DATABASE = "your_database_name"
        self.USER = "your_username"
        self.PASSWORD = "your_password"
        self.connection = None

    def connect(self):
        """Connects to the PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(
                host=self.HOST, database=self.DATABASE, user=self.USER, password=self.PASSWORD
            )
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False

    def close_connection(self):
        """Closes the connection to the database"""
        if self.connection:
            self.connection.close()

    def execute_query(self, query, params=None):
        """Executes a query with optional parameters and commits changes"""
        if not self.connect():
            return False

        cursor = self.connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error executing query: {e}")
            return False
        finally:
            self.close_connection()

    # Create functions
    def create_user(self, username, name, user_id, number, language_code, email, password, balance):
        """Creates a new user in the User table"""
        query = """
            INSERT INTO User (username, name, user_id, number, language_code, email, password, balance, is_authenticated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """
        return self.execute_query(query, (username, name, user_id, number, language_code, email, password, balance))

    def create_order(self, user_id, product_id, is_completed):
        """Creates a new order in the Order table"""
        query = """
            INSERT INTO Order (user_id, product_id, time, is_completed)
            VALUES (%s, %s, current_timestamp, %s)
            """
        return self.execute_query(query, (user_id, product_id, is_completed))

    def create_product(self, app_id, name, quantity, price):
        """Creates a new product in the Product table"""
        query = """
            INSERT INTO Product (app_id, name, quantity, price)
            VALUES (%s, %s, %s, %s)
            """
        return self.execute_query(query, (app_id, name, quantity, price))

    def create_app(self, title, photo):  # Assuming photo is a reference ID
        """Creates a new app in the Apps table"""
        query = """
            INSERT INTO Apps (title, photo)
            VALUES (%s, %s)
            """
        return self.execute_query(query, (title, photo))

    def create_payment(self, user_id, time, price, cheque_pic, is_accepted):
        """Creates a new payment in the Payment table"""
        query = """
            INSERT INTO Payment (user_id, time, price, cheque_pic, is_accepted)
            VALUES (%s, %s, %s, %s, %s)
            """
        return self.execute_query(query, (user_id, time, price, cheque_pic, is_accepted))

    # Read functions
    def get_user(self, user_id):
        """Gets a user by ID from the User table"""
        query = """
            SELECT * FROM User
            WHERE id = %s
            """
        return self.execute_query(query, (user_id,))  # Single value in a tuple

    def get_order(self, order_id):
        """Gets an order by ID from the Order table"""
        query = """
            SELECT * FROM Order
            WHERE id = %s
            """
        return self.execute_query(query, (order_id,))

    def get_all_users(self):
        """Gets all users from the User table"""
        query = """
            SELECT * FROM User
            """
        return self.execute_query(query)

    def get_all_orders(self):
        """Gets all orders from the Order table"""
        query = """
            SELECT * FROM Order
            """
        return self.execute_query(query)

    def get_user_orders(self, user_id):
        """Gets all orders for a specific user from the Order table"""
        query = """
            SELECT * FROM Order
            WHERE user_id = %s
            """
        return self.execute_query(query, (user_id,))

    def get_user_payments(self, user_id):
        """Gets all payments for a specific user from the Payment table"""
        query = """
            SELECT * FROM Payment
            WHERE user_id = %s
            """
        return self.execute_query(query, (user_id,))

    # Update functions
    def edit_user(self, user_id, update_data):
        """Updates a user's information in the User table"""
        # update_data should be a dictionary with key-value pairs for update
        # e.g., update_data = {"name": "New Name", "email": "new_email@example.com"}
        query = "UPDATE User SET " + ", ".join(f"{k} = %({k})s" for k in update_data.keys()) + " WHERE id = %s"
        params = list(update_data.values()) + [user_id]  # Combine update values and user ID
        return self.execute_query(query, params)

    def edit_order(self, order_id, update_data):
        """Updates an order's information in the Order table"""
        # update_data should be a dictionary with key-value pairs for update
        # (similar to edit_user)
        query = "UPDATE Order SET " + ", ".join(f"{k} = %({k})s" for k in update_data.keys()) + " WHERE id = %s"
        params = list(update_data.values()) + [order_id]  # Combine update values and order ID
        return self.execute_query(query, params)
