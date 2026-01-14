import customtkinter as ctk
import sqlite3
import csv
from datetime import datetime
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from fpdf import FPDF  # BIBLIOTECA NOVA

# Configurações Visuais
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")


# --- CLASSE PARA GERAR O PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatorio Financeiro - CONTROLE DE GASTOS', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')


# --- BANCO DE DADOS ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("financas.db", timeout=10)
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
        self.cursor.execute("""
                            CREATE TABLE IF NOT EXISTS usuarios
                            (
                                id
                                INTEGER
                                PRIMARY
                                KEY
                                AUTOINCREMENT,
                                usuario
                                TEXT
                                UNIQUE
                                NOT
                                NULL,
                                senha
                                TEXT
                                NOT
                                NULL,
                                is_admin
                                INTEGER
                                DEFAULT
                                0
                            )
                            """)
        try:
            self.cursor.execute("INSERT INTO usuarios (usuario, senha, is_admin) VALUES (?, ?, ?)",
                                ('admin', '1234', 1))
            self.conn.commit()
        except sqlite3.IntegrityError:
            pass

    def fechar_conexao(self):
        self.conn.close()

    def verificar_login(self, usuario, senha):
        self.cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (usuario, senha))
        return self.cursor.fetchone()

    def cadastrar_usuario(self, usuario, senha, is_admin=0):
        try:
            self.cursor.execute("INSERT INTO usuarios (usuario, senha, is_admin) VALUES (?, ?, ?)",
                                (usuario, senha, is_admin))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def listar_nomes_usuarios(self):
        self.cursor.execute("SELECT usuario FROM usuarios")
        return [row[0] for row in self.cursor.fetchall()]

    def alterar_senha(self, usuario, nova_senha):
        self.cursor.execute("UPDATE usuarios SET senha=? WHERE usuario=?", (nova_senha, usuario))
        self.conn.commit()

    # --- Métodos Financeiros ---
    def adicionar_movimento(self, t, v, d, c, dt):
        self.cursor.execute(
            "INSERT INTO movimentos (tipo, valor, descricao, categoria, data_iso) VALUES (?, ?, ?, ?, ?)",
            (t, v, d, c, dt))
        self.conn.commit()

    def atualizar_movimento(self, id_m, t, v, d, c, dt):
        self.cursor.execute("UPDATE movimentos SET tipo=?, valor=?, descricao=?, categoria=?, data_iso=? WHERE id=?",
                            (t, v, d, c, dt, id_m))
        self.conn.commit()

    def obter_por_mes(self, mes, ano):
        filtro = f"{ano}-{mes:02d}%"
        self.cursor.execute("SELECT * FROM movimentos WHERE data_iso LIKE ? ORDER BY data_iso DESC", (filtro,))
        return self.cursor.fetchall()

    def deletar_movimento(self, id_item):
        self.cursor.execute("DELETE FROM movimentos WHERE id=?", (id_item,))
        self.conn.commit()

    def obter_resumo_mes(self, mes, ano):
        filtro = f"{ano}-{mes:02d}%"
        self.cursor.execute("SELECT SUM(valor) FROM movimentos WHERE tipo='Receita' AND data_iso LIKE ?", (filtro,))
        receita = self.cursor.fetchone()[0] or 0.0
        self.cursor.execute("SELECT SUM(valor) FROM movimentos WHERE tipo='Despesa' AND data_iso LIKE ?", (filtro,))
        despesa = self.cursor.fetchone()[0] or 0.0
        return receita, despesa, receita - despesa

    def obter_gastos_categoria_mes(self, mes, ano):
        filtro = f"{ano}-{mes:02d}%"
        self.cursor.execute("""
                            SELECT categoria, SUM(valor)
                            FROM movimentos
                            WHERE tipo = 'Despesa'
                              AND data_iso LIKE ?
                            GROUP BY categoria
                            ORDER BY SUM(valor) DESC
                            """, (filtro,))
        return self.cursor.fetchall()


# --- JANELA DE CONFIGURAÇÕES ---
class ConfiguracoesWindow(ctk.CTkToplevel):
    def __init__(self, parent_db):
        super().__init__()
        self.db = parent_db
        self.title("Painel de Configurações")
        self.geometry("400x350")
        self.attributes('-topmost', True)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_cadastro = self.tabview.add("Novo Usuário")
        self.tab_senha = self.tabview.add("Alterar Senhas")

        # ABA 1
        ctk.CTkLabel(self.tab_cadastro, text="Criar Acesso", font=("Roboto", 14, "bold")).pack(pady=10)
        self.entry_new_user = ctk.CTkEntry(self.tab_cadastro, placeholder_text="Nome de Usuário")
        self.entry_new_user.pack(pady=5)
        self.entry_new_pass = ctk.CTkEntry(self.tab_cadastro, placeholder_text="Senha")
        self.entry_new_pass.pack(pady=5)
        self.chk_admin_var = ctk.IntVar(value=0)
        ctk.CTkCheckBox(self.tab_cadastro, text="É Admin?", variable=self.chk_admin_var).pack(pady=10)
        ctk.CTkButton(self.tab_cadastro, text="Salvar Usuário", command=self.salvar_user, fg_color="#10ac84").pack(
            pady=10)

        # ABA 2
        ctk.CTkLabel(self.tab_senha, text="Gerenciar Senhas", font=("Roboto", 14, "bold")).pack(pady=10)
        ctk.CTkLabel(self.tab_senha, text="Selecione o Usuário:").pack()
        lista_users = self.db.listar_nomes_usuarios()
        self.combo_users = ctk.CTkOptionMenu(self.tab_senha, values=lista_users)
        self.combo_users.pack(pady=5)
        self.entry_change_pass = ctk.CTkEntry(self.tab_senha, placeholder_text="Nova Senha")
        self.entry_change_pass.pack(pady=10)
        ctk.CTkButton(self.tab_senha, text="Atualizar Senha", command=self.mudar_senha, fg_color="#e67e22").pack(
            pady=10)

    def salvar_user(self):
        user = self.entry_new_user.get()
        senha = self.entry_new_pass.get()
        if not user or not senha:
            messagebox.showwarning("Atenção", "Preencha tudo!")
            return
        if self.db.cadastrar_usuario(user, senha, self.chk_admin_var.get()):
            messagebox.showinfo("Sucesso", f"Usuário {user} criado!")
            self.combo_users.configure(values=self.db.listar_nomes_usuarios())
            self.entry_new_user.delete(0, 'end');
            self.entry_new_pass.delete(0, 'end')
        else:
            messagebox.showerror("Erro", "Usuário já existe!")

    def mudar_senha(self):
        target_user = self.combo_users.get()
        new_pass = self.entry_change_pass.get()
        if not new_pass:
            messagebox.showwarning("Erro", "Digite a nova senha.")
            return
        self.db.alterar_senha(target_user, new_pass)
        messagebox.showinfo("Sucesso", f"Senha de '{target_user}' atualizada!")
        self.entry_change_pass.delete(0, 'end')


# --- TELA DE LOGIN ---
class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.title("Login Seguro")
        self.geometry("400x400")
        self.resizable(False, False)
        self.eval('tk::PlaceWindow . center')

        ctk.CTkLabel(self, text="CONTROLE DE GASTOS", font=("Roboto", 24, "bold"), text_color="#2cc985").pack(
            pady=(50, 10))
        ctk.CTkLabel(self, text="Sistema Financeiro Corporativo", font=("Roboto", 12)).pack(pady=(0, 40))

        self.entry_user = ctk.CTkEntry(self, placeholder_text="Usuário", width=250, height=40)
        self.entry_user.pack(pady=10)
        self.entry_pass = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=250, height=40)
        self.entry_pass.pack(pady=10)

        ctk.CTkButton(self, text="ENTRAR", width=250, height=40, fg_color="#10ac84", hover_color="#0d8c6b",
                      command=self.logar).pack(pady=30)

    def logar(self):
        user = self.entry_user.get()
        senha = self.entry_pass.get()
        dados = self.db.verificar_login(user, senha)

        if dados:
            is_admin = dados[3]
            self.db.fechar_conexao()
            self.destroy()
            app = FinanceApp(user_admin=is_admin, nome_user=user)
            app.mainloop()
        else:
            messagebox.showerror("Erro", "Acesso Negado.")


# --- APLICAÇÃO PRINCIPAL ---
class FinanceApp(ctk.CTk):
    def __init__(self, user_admin, nome_user):
        super().__init__()
        self.db = Database()
        self.is_admin = user_admin
        self.nome_user = nome_user

        self.title("Controle Financeiro Profissional")
        self.geometry("1100x700")

        self.id_em_edicao = None
        self.ano_visualizacao = datetime.now().year
        self.mes_visualizacao = datetime.now().month
        self.color_panel = "#2b2b2b"
        self.configure(fg_color="#1a1a1a")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # BARRA LATERAL COM ROLAGEM
        self.frame_left = ctk.CTkScrollableFrame(self, width=220, corner_radius=0, fg_color=self.color_panel)
        self.frame_left.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.frame_left, text="CONTROLE\nDE GASTOS", font=("Roboto", 20, "bold")).pack(pady=30)

        self.criar_label_input("Tipo:")
        self.tipo_var = ctk.StringVar(value="Receita")
        ctk.CTkOptionMenu(self.frame_left, variable=self.tipo_var, values=["Receita", "Despesa"], fg_color="#3a3a3a",
                          button_color="#2cc985").pack(pady=5, padx=20, fill="x")

        self.criar_label_input("Valor (R$):")
        self.entry_valor = ctk.CTkEntry(self.frame_left, placeholder_text="0.00");
        self.entry_valor.pack(pady=5, padx=20, fill="x")
        self.criar_label_input("Descrição:")
        self.entry_desc = ctk.CTkEntry(self.frame_left);
        self.entry_desc.pack(pady=5, padx=20, fill="x")
        self.criar_label_input("Categoria:")
        self.entry_cat = ctk.CTkEntry(self.frame_left);
        self.entry_cat.pack(pady=5, padx=20, fill="x")
        self.criar_label_input("Data:")
        self.entry_data = ctk.CTkEntry(self.frame_left)
        self.entry_data.insert(0, datetime.today().strftime('%Y-%m-%d'));
        self.entry_data.pack(pady=5, padx=20, fill="x")

        self.btn_submit = ctk.CTkButton(self.frame_left, text="SALVAR", command=self.submeter_dados, fg_color="#10ac84",
                                        height=40)
        self.btn_submit.pack(pady=(30, 10), padx=20, fill="x")
        ctk.CTkButton(self.frame_left, text="Limpar", command=self.resetar_formulario, fg_color="transparent",
                      border_width=1, text_color="#a0a0a0").pack(pady=5, padx=20, fill="x")

        # Botões de Exportação
        ctk.CTkButton(self.frame_left, text="📥 Excel", command=self.exportar_excel, fg_color="#27ae60").pack(
            pady=(20, 5), padx=20, fill="x")
        ctk.CTkButton(self.frame_left, text="📄 PDF Pro", command=self.exportar_pdf, fg_color="#c0392b",
                      hover_color="#e74c3c").pack(pady=5, padx=20, fill="x")

        if self.is_admin == 1:
            ctk.CTkFrame(self.frame_left, height=2, fg_color="gray").pack(fill="x", pady=20, padx=20)
            ctk.CTkButton(self.frame_left, text="⚙ Configurações", command=self.abrir_configuracoes, fg_color="#34495e",
                          hover_color="#2c3e50").pack(pady=10, padx=20, fill="x")

        # ÁREA DIREITA
        self.frame_right = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_right.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # KPIs
        self.frame_kpi = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        self.frame_kpi.pack(fill="x", pady=(0, 20))
        self.card_receita = self.criar_card_kpi(self.frame_kpi, "ENTRADAS", "R$ 0.00", "#2cc985")
        self.card_despesa = self.criar_card_kpi(self.frame_kpi, "SAÍDAS", "R$ 0.00", "#ff5e57")
        self.card_saldo = self.criar_card_kpi(self.frame_kpi, "SALDO", "R$ 0.00", "#3498db")

        # Centro
        self.frame_centro = ctk.CTkFrame(self.frame_right, fg_color="transparent")
        self.frame_centro.pack(fill="both", expand=True)
        self.frame_tabela = ctk.CTkFrame(self.frame_centro, fg_color=self.color_panel)
        self.frame_tabela.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Navegação
        self.frame_head_tab = ctk.CTkFrame(self.frame_tabela, fg_color="transparent")
        self.frame_head_tab.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(self.frame_head_tab, text="<", width=30, command=lambda: self.mudar_mes(-1)).pack(side="left")
        self.lbl_mes_ano = ctk.CTkLabel(self.frame_head_tab, text="...", font=("Roboto", 16, "bold"))
        self.lbl_mes_ano.pack(side="left", padx=10)
        ctk.CTkButton(self.frame_head_tab, text=">", width=30, command=lambda: self.mudar_mes(1)).pack(side="left")
        ctk.CTkButton(self.frame_head_tab, text="✖", width=40, fg_color="#ff4757",
                      command=self.excluir_selecionado).pack(side="right", padx=5)
        ctk.CTkButton(self.frame_head_tab, text="✎", width=40, fg_color="#f39c12", command=self.preparar_edicao).pack(
            side="right", padx=5)

        # Tabela
        style = ttk.Style();
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", borderwidth=0,
                        rowheight=25)
        style.configure("Treeview.Heading", background="#3a3a3a", foreground="white", borderwidth=1,
                        font=("Roboto", 10, "bold"))
        style.map("Treeview", background=[("selected", "#1f6aa5")])
        cols = ("ID", "Tipo", "Valor", "Desc", "Cat", "Data")
        self.tree = ttk.Treeview(self.frame_tabela, columns=cols, show="headings")
        self.tree.heading("ID", text="ID");
        self.tree.column("ID", width=30)
        self.tree.heading("Tipo", text="Tipo");
        self.tree.column("Tipo", width=70)
        self.tree.heading("Valor", text="Valor");
        self.tree.column("Valor", width=80)
        self.tree.heading("Desc", text="Descrição");
        self.tree.column("Desc", width=120)
        self.tree.heading("Cat", text="Categoria");
        self.tree.column("Cat", width=100)
        self.tree.heading("Data", text="Data");
        self.tree.column("Data", width=80)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Gráfico
        self.frame_grafico = ctk.CTkFrame(self.frame_centro, fg_color=self.color_panel, width=300)
        self.frame_grafico.pack(side="right", fill="both", expand=False)
        ctk.CTkLabel(self.frame_grafico, text="Gráfico de Despesas", font=("Roboto", 14, "bold")).pack(pady=10)
        self.area_plt = ctk.CTkFrame(self.frame_grafico, fg_color="transparent")
        self.area_plt.pack(fill="both", expand=True, padx=10, pady=10)

        self.atualizar_titulo_mes()
        self.carregar_dados()

    # Helpers
    def abrir_configuracoes(self):
        ConfiguracoesWindow(self.db)

    def criar_label_input(self, texto):
        ctk.CTkLabel(self.frame_left, text=texto, text_color="#a0a0a0", anchor="w", font=("Roboto", 11)).pack(padx=20,
                                                                                                              pady=(5,
                                                                                                                    0),
                                                                                                              fill="x")

    def criar_card_kpi(self, parent, titulo, valor, cor):
        card = ctk.CTkFrame(parent, fg_color=self.color_panel);
        card.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkFrame(card, fg_color=cor, height=5, corner_radius=0).pack(fill="x", side="top")
        ctk.CTkLabel(card, text=titulo, font=("Roboto", 12), text_color="gray").pack(pady=(5, 0))
        lbl = ctk.CTkLabel(card, text=valor, font=("Roboto", 20, "bold"));
        lbl.pack(pady=(0, 5))
        return lbl

    def submeter_dados(self):
        try:
            t, v, d, c, dt = self.tipo_var.get(), float(self.entry_valor.get().replace(",",
                                                                                       ".")), self.entry_desc.get(), self.entry_cat.get(), self.entry_data.get()
            if self.id_em_edicao:
                self.db.atualizar_movimento(self.id_em_edicao, t, v, d, c, dt)
            else:
                self.db.adicionar_movimento(t, v, d, c, dt)
            self.resetar_formulario();
            self.carregar_dados();
            messagebox.showinfo("OK", "Salvo!")
        except:
            messagebox.showerror("Erro", "Verifique os dados.")

    def carregar_dados(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for r in self.db.obter_por_mes(self.mes_visualizacao, self.ano_visualizacao): self.tree.insert("", "end",
                                                                                                       values=r)
        rec, desp, saldo = self.db.obter_resumo_mes(self.mes_visualizacao, self.ano_visualizacao)
        self.card_receita.configure(text=f"R$ {rec:,.2f}");
        self.card_despesa.configure(text=f"R$ {desp:,.2f}")
        self.card_saldo.configure(text=f"R$ {saldo:,.2f}", text_color="#2cc985" if saldo >= 0 else "#ff5e57")
        self.gerar_grafico()

    def gerar_grafico(self):
        for w in self.area_plt.winfo_children(): w.destroy()
        dados_raw = self.db.obter_gastos_categoria_mes(self.mes_visualizacao, self.ano_visualizacao)

        if not dados_raw:
            ctk.CTkLabel(self.area_plt, text="Sem despesas neste mês", text_color="gray").pack(expand=True)
            return

        categorias = []
        valores = []
        for row in dados_raw:
            cat_nome = row[0]
            if not cat_nome or cat_nome.strip() == "": cat_nome = "(Sem Categoria)"
            categorias.append(cat_nome)
            valores.append(row[1])

        fig, ax = plt.subplots(figsize=(3.5, 3.5), dpi=80)
        fig.patch.set_facecolor('#2b2b2b');
        ax.set_facecolor('#2b2b2b')
        wedges, texts, autotexts = ax.pie(valores, labels=categorias, autopct='%1.1f%%', startangle=90,
                                          textprops={'color': "white"})
        for autotext in autotexts: autotext.set_color('black'); autotext.set_fontweight('bold')
        ax.set_title(f"Total: R$ {sum(valores):.2f}", color="white", fontsize=10)

        canvas = FigureCanvasTkAgg(fig, master=self.area_plt)
        canvas.draw();
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def preparar_edicao(self):
        sel = self.tree.selection()
        if sel:
            v = self.tree.item(sel)['values']
            self.id_em_edicao = v[0];
            self.tipo_var.set(v[1])
            self.entry_valor.delete(0, "end");
            self.entry_valor.insert(0, v[2])
            self.entry_desc.delete(0, "end");
            self.entry_desc.insert(0, v[3])
            self.entry_cat.delete(0, "end");
            self.entry_cat.insert(0, v[4])
            self.entry_data.delete(0, "end");
            self.entry_data.insert(0, v[5])
            self.btn_submit.configure(text="ATUALIZAR", fg_color="#2980b9")

    def resetar_formulario(self):
        self.id_em_edicao = None;
        self.entry_valor.delete(0, "end");
        self.entry_desc.delete(0, "end");
        self.entry_cat.delete(0, "end")
        self.btn_submit.configure(text="SALVAR", fg_color="#10ac84")

    def excluir_selecionado(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Excluir", "Apagar registro?"):
            self.db.deletar_movimento(self.tree.item(sel)['values'][0]);
            self.carregar_dados()

    def exportar_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f, delimiter=';');
                w.writerow(["ID", "Tipo", "Valor", "Desc", "Cat", "Data"])
                w.writerows(self.db.obter_por_mes(self.mes_visualizacao, self.ano_visualizacao))
            messagebox.showinfo("Sucesso", "Exportado!")

    # --- FUNÇÃO NOVA DE EXPORTAR PDF ---
    def exportar_pdf(self):
        dados = self.db.obter_por_mes(self.mes_visualizacao, self.ano_visualizacao)
        if not dados:
            messagebox.showwarning("Aviso", "Sem dados para gerar relatório!")
            return

        caminho = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF File", "*.pdf")])
        if not caminho:
            return

        pdf = PDF()
        pdf.add_page()

        # Info do Mês
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Periodo: {self.mes_visualizacao}/{self.ano_visualizacao}", 0, 1)
        pdf.ln(5)

        # Cabeçalho da Tabela
        pdf.set_font("Arial", "B", 10)
        pdf.set_fill_color(200, 220, 255)  # Azul claro
        pdf.cell(20, 10, "Tipo", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Valor", 1, 0, 'C', 1)
        pdf.cell(60, 10, "Descricao", 1, 0, 'C', 1)
        pdf.cell(40, 10, "Categoria", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Data", 1, 1, 'C', 1)

        # Linhas da Tabela
        pdf.set_font("Arial", "", 10)
        rec, desp, saldo = self.db.obter_resumo_mes(self.mes_visualizacao, self.ano_visualizacao)

        for row in dados:
            # row: (id, tipo, valor, desc, cat, data)
            pdf.cell(20, 10, row[1], 1, 0, 'C')
            pdf.cell(30, 10, f"R$ {row[2]:.2f}", 1, 0, 'C')
            pdf.cell(60, 10, str(row[3])[:30], 1, 0, 'L')  # Corta descrição longa
            pdf.cell(40, 10, str(row[4])[:20], 1, 0, 'C')
            pdf.cell(30, 10, row[5], 1, 1, 'C')

        # Resumo Final
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "RESUMO FINAL", 0, 1)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Total Receitas: R$ {rec:.2f}", 0, 1)
        pdf.cell(0, 10, f"Total Despesas: R$ {desp:.2f}", 0, 1)

        pdf.set_text_color(0, 150, 0) if saldo >= 0 else pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 10, f"Saldo Liquido: R$ {saldo:.2f}", 0, 1)

        try:
            pdf.output(caminho)
            messagebox.showinfo("Sucesso", "Relatório PDF gerado com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar PDF: {e}")

    def mudar_mes(self, d):
        self.mes_visualizacao += d
        if self.mes_visualizacao > 12:
            self.mes_visualizacao = 1; self.ano_visualizacao += 1
        elif self.mes_visualizacao < 1:
            self.mes_visualizacao = 12; self.ano_visualizacao -= 1
        self.atualizar_titulo_mes();
        self.carregar_dados()

    def atualizar_titulo_mes(self):
        self.lbl_mes_ano.configure(text=f"{self.mes_visualizacao}/{self.ano_visualizacao}")


if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()