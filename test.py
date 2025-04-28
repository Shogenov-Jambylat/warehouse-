import psycopg2
from tkinter import *
from tkinter import ttk, messagebox, simpledialog

# Настройки подключения к базе данных
DB_SETTINGS = {
    "dbname": "bot2",
    "user": "postgres",
    "password": "1234",
    "host": "127.0.0.1",
    "port": 5433
}

def connect_db():
    """Устанавливает соединение с базой данных."""
    return psycopg2.connect(**DB_SETTINGS)

def init_db():
    """Инициализирует базу данных (создает таблицы, если их нет)."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price NUMERIC(10, 2) NOT NULL,
                    quantity INTEGER NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id),
                    sold_quantity INTEGER NOT NULL,
                    sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()

# Основные функции работы с БД
def fetch_products():
    """Получает список всех товаров."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, price, quantity FROM products")
            return cur.fetchall()

def add_product(name, price, quantity):
    """Добавляет новый товар."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO products (name, price, quantity) VALUES (%s, %s, %s)",
                (name, price, quantity)
            )
        conn.commit()

def update_product(product_id, name, price, quantity):
    """Обновляет данные товара."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE products SET name = %s, price = %s, quantity = %s WHERE id = %s",
                (name, price, quantity, product_id)
            )
        conn.commit()

def delete_product(product_id):
    """Удаляет товар и связанные с ним записи о продажах."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            # Сначала удалить связанные продажи
            cur.execute("DELETE FROM sales WHERE product_id = %s", (product_id,))
            # Затем удалить сам продукт
            cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()

def sell_product(product_id, quantity):
    """Продает товар."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT quantity FROM products WHERE id = %s", (product_id,))
            available_quantity = cur.fetchone()[0]
            if quantity > available_quantity:
                raise ValueError("Недостаточно товара на складе")
            cur.execute("UPDATE products SET quantity = quantity - %s WHERE id = %s", (quantity, product_id))
            cur.execute(
                "INSERT INTO sales (product_id, sold_quantity) VALUES (%s, %s)",
                (product_id, quantity)
            )
        conn.commit()

def fetch_sales():
    """Получает список всех продаж."""
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.id, p.name, s.sold_quantity, s.sale_date
                FROM sales s
                JOIN products p ON s.product_id = p.id
            """)
            return cur.fetchall()

# Интерфейс
def main_window():
    root = Tk()
    root.title("Управление складом")

    # Функции интерфейса
    def refresh_products():
        for row in product_table.get_children():
            product_table.delete(row)
        for product in fetch_products():
            product_table.insert("", "end", values=product)

    def add_product_window():
        def save_product():
            try:
                name = name_entry.get()
                price = float(price_entry.get())
                quantity = int(quantity_entry.get())
                add_product(name, price, quantity)
                refresh_products()
                add_window.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить продукт: {e}")

        add_window = Toplevel(root)
        add_window.title("Добавить продукт")
        Label(add_window, text="Название").grid(row=0, column=0)
        name_entry = Entry(add_window)
        name_entry.grid(row=0, column=1)

        Label(add_window, text="Цена").grid(row=1, column=0)
        price_entry = Entry(add_window)
        price_entry.grid(row=1, column=1)

        Label(add_window, text="Количество").grid(row=2, column=0)
        quantity_entry = Entry(add_window)
        quantity_entry.grid(row=2, column=1)

        Button(add_window, text="Сохранить", command=save_product).grid(row=3, column=0, columnspan=2)

    def delete_selected_product():
        selected_item = product_table.selection()
        if not selected_item:
            messagebox.showerror("Ошибка", "Выберите продукт для удаления.")
            return
        product_id = product_table.item(selected_item)["values"][0]
        delete_product(product_id)
        refresh_products()

    def sell_selected_product():
        selected_item = product_table.selection()
        if not selected_item:
            messagebox.showerror("Ошибка", "Выберите продукт для продажи.")
            return
        product_id = product_table.item(selected_item)["values"][0]
        quantity = simpledialog.askinteger("Продажа", "Введите количество:")
        if quantity:
            try:
                sell_product(product_id, quantity)
                refresh_products()
            except ValueError as e:
                messagebox.showerror("Ошибка", str(e))

    def view_sales():
        sales = fetch_sales()
        sales_window = Toplevel(root)
        sales_window.title("Продажи")
        sales_table = ttk.Treeview(sales_window, columns=("ID", "Товар", "Количество", "Дата"), show="headings")
        sales_table.heading("ID", text="ID")
        sales_table.heading("Товар", text="Товар")
        sales_table.heading("Количество", text="Количество")
        sales_table.heading("Дата", text="Дата")
        sales_table.pack(fill=BOTH, expand=True)

        for sale in sales:
            sales_table.insert("", "end", values=sale)

    # Таблица товаров
    product_table = ttk.Treeview(root, columns=("ID", "Название", "Цена", "Количество"), show="headings")
    product_table.heading("ID", text="ID")
    product_table.heading("Название", text="Название")
    product_table.heading("Цена", text="Цена")
    product_table.heading("Количество", text="Количество")
    product_table.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Кнопки управления
    Button(root, text="Добавить продукт", command=add_product_window).pack(side=LEFT, padx=15, pady=15)
    Button(root, text="Удалить продукт", command=delete_selected_product).pack(side=LEFT, padx=5, pady=5)
    Button(root, text="Продать продукт", command=sell_selected_product).pack(side=LEFT, padx=5, pady=5)
    Button(root, text="Просмотреть продажи", command=view_sales).pack(side=LEFT, padx=5, pady=5)
    Button(root, text="Обновить", command=refresh_products).pack(side=LEFT, padx=5, pady=5)

    refresh_products()
    root.mainloop()

if __name__ == "__main__":
    init_db()
    main_window()