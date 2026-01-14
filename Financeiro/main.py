import flet as ft
import sqlite3
from datetime import datetime


# --- BANCO DE DADOS ---
class Database:
    def __init__(self):
        # check_same_thread=False é essencial para Flet na Web
        self.conn = sqlite3.connect("financas.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.criar_tabelas()

    def criar_tabelas(self):
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS movimentos
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                tipo
                                TEXT
                                NOT
                                NULL,
                                valor
                                REAL
                                NOT
                                NULL,
                                descricao
                                TEXT,
                                categoria
                                TEXT,
                                data_iso
                                TEXT
                            )
                            """)
        self.conn.commit()

    def adicionar_movimento(self, t, v, d, c, dt):
        self.cursor.execute(
            "INSERT INTO movimentos (tipo, valor, descricao, categoria, data_iso) VALUES (?, ?, ?, ?, ?)",
            (t, v, d, c, dt))
        self.conn.commit()

    def deletar_movimento(self, id_item):
        self.cursor.execute("DELETE FROM movimentos WHERE id=?", (id_item,))
        self.conn.commit()

    def obter_todos(self):
        self.cursor.execute("SELECT * FROM movimentos ORDER BY data_iso DESC")
        return self.cursor.fetchall()

    def obter_resumo(self):
        self.cursor.execute("SELECT SUM(valor) FROM movimentos WHERE tipo='Receita'")
        rec = self.cursor.fetchone()[0] or 0.0
        self.cursor.execute("SELECT SUM(valor) FROM movimentos WHERE tipo='Despesa'")
        desp = self.cursor.fetchone()[0] or 0.0
        return rec, desp, rec - desp


# --- APLICAÇÃO VISUAL (FLET) ---
def main(page: ft.Page):
    # Configurações da Página
    page.title = "Controle MNS"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    page.scroll = "adaptive"  # Permite rolar a tela no celular

    db = Database()

    # --- ELEMENTOS (Inputs) ---
    dd_tipo = ft.Dropdown(
        options=[ft.dropdown.Option("Receita"), ft.dropdown.Option("Despesa")],
        value="Receita",
        width=150,
        label="Tipo"
    )

    txt_valor = ft.TextField(label="Valor (R$)", width=150, keyboard_type=ft.KeyboardType.NUMBER)
    txt_desc = ft.TextField(label="Descrição", expand=True)
    txt_cat = ft.TextField(label="Categoria", width=150)
    txt_data = ft.TextField(label="Data", value=datetime.today().strftime('%Y-%m-%d'), width=150)

    # --- ELEMENTOS (Resumo) ---
    lbl_saldo = ft.Text("R$ 0.00", size=25, weight="bold", color="blue")

    container_resumo = ft.Container(
        content=ft.Column([
            ft.Text("SALDO ATUAL", size=12, color="grey"),
            lbl_saldo
        ], alignment=ft.MainAxisAlignment.CENTER),
        padding=15,
        bgcolor=ft.colors.SURFACE_VARIANT,
        border_radius=10,
        width=float("inf")  # Ocupa toda a largura
    )

    # --- ELEMENTOS (Lista) ---
    lista_movimentos = ft.ListView(expand=True, spacing=10)

    # --- FUNÇÕES ---
    def deletar_item(e):
        id_del = e.control.data
        db.deletar_movimento(id_del)
        atualizar_dados()

    def atualizar_dados():
        lista_movimentos.controls.clear()
        dados = db.obter_todos()

        for row in dados:
            id_mov, tipo, valor, desc, cat, data = row

            # Ícone e Cor baseados no tipo
            icone = ft.icons.ARROW_CIRCLE_UP if tipo == "Receita" else ft.icons.ARROW_CIRCLE_DOWN
            cor_icone = "green" if tipo == "Receita" else "red"

            # Card bonito para cada movimento
            card = ft.Card(
                content=ft.Container(
                    content=ft.Row([
                        ft.Icon(icone, color=cor_icone, size=30),
                        ft.Column([
                            ft.Text(desc, weight="bold", size=16),
                            ft.Text(f"{cat} • {data}", size=12, color="grey"),
                        ], expand=True),
                        ft.Column([
                            ft.Text(f"R$ {valor:.2f}", weight="bold", color=cor_icone),
                            ft.IconButton(
                                icon=ft.icons.DELETE_OUTLINE,
                                icon_color="red",
                                icon_size=20,
                                data=id_mov,
                                on_click=deletar_item
                            )
                        ], alignment=ft.MainAxisAlignment.END),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10
                )
            )
            lista_movimentos.controls.append(card)

        # Atualiza Saldo
        rec, desp, saldo = db.obter_resumo()
        lbl_saldo.value = f"R$ {saldo:.2f}"
        lbl_saldo.color = "green" if saldo >= 0 else "red"

        page.update()

    def adicionar_click(e):
        if not txt_valor.value:
            page.snack_bar = ft.SnackBar(ft.Text("Digite um valor!"), bgcolor="red")
            page.snack_bar.open = True
            page.update()
            return

        try:
            val = float(txt_valor.value.replace(",", "."))
            db.adicionar_movimento(dd_tipo.value, val, txt_desc.value, txt_cat.value, txt_data.value)

            # Limpa e foca
            txt_valor.value = ""
            txt_desc.value = ""
            txt_valor.focus()

            page.snack_bar = ft.SnackBar(ft.Text("Salvo!"), bgcolor="green")
            page.snack_bar.open = True
            atualizar_dados()
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Valor inválido"), bgcolor="red")
            page.snack_bar.open = True
            page.update()

    btn_add = ft.ElevatedButton("Adicionar", on_click=adicionar_click, icon=ft.icons.ADD, height=50, width=float("inf"))

    # --- LAYOUT FINAL ---
    page.add(
        ft.Text("Financeiro MNS", size=22, weight="bold"),
        container_resumo,
        ft.Divider(),
        ft.Row([dd_tipo, txt_valor], wrap=True),
        ft.Row([txt_desc, txt_cat], wrap=True),
        txt_data,
        btn_add,
        ft.Divider(),
        ft.Text("Histórico", size=18, weight="bold"),
        lista_movimentos
    )

    atualizar_dados()


# --- INICIALIZAÇÃO SEGURA ---
if __name__ == "__main__":
    print("--- SERVIDOR INICIADO ---")
    print("Acesse no celular pelo IP do seu PC.")
    print("Se aparecer o logo do Flet girando, aguarde (pode demorar na 1ª vez).")
    print("-------------------------")

    # Versão sem especificar renderer (deixa o Flet escolher o melhor)
    # Ignora o aviso de 'DeprecationWarning', ele vai funcionar.
    try:
        ft.app(target=main, view="web_browser", port=8000, host="0.0.0.0")
    except Exception as e:
        print(f"Erro Fatal: {e}")
        input("Pressione Enter para sair...")