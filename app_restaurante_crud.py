import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# =========================================================
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="Gestão do Restaurante",
    page_icon="🍽️",
    layout="wide",
)

DB_PATH = Path(__file__).with_name("restaurante.db")


# =========================================================
# BANCO DE DADOS
# =========================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                tipo TEXT NOT NULL DEFAULT 'Ambos',
                descricao TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS fornecedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                documento TEXT,
                telefone TEXT,
                email TEXT,
                contato TEXT,
                observacoes TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS contas_pagar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                fornecedor_id INTEGER,
                categoria_id INTEGER,
                valor REAL NOT NULL DEFAULT 0,
                vencimento TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pendente',
                data_pagamento TEXT,
                forma_pagamento TEXT,
                observacoes TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE SET NULL,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                sku TEXT,
                categoria_id INTEGER,
                fornecedor_id INTEGER,
                unidade TEXT NOT NULL DEFAULT 'un',
                quantidade REAL NOT NULL DEFAULT 0,
                estoque_minimo REAL NOT NULL DEFAULT 0,
                custo_medio REAL NOT NULL DEFAULT 0,
                localizacao TEXT,
                observacoes TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL,
                FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id) ON DELETE SET NULL
            );
            """
        )


def query_df(sql, params=()):
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def execute(sql, params=()):
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def money_br(value):
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def rerun():
    st.rerun()


def row_to_dict(row):
    return dict(row) if row else {}


def fetch_one(table, row_id):
    with get_conn() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone()
        return row_to_dict(row)


def category_options(include_inactive=False):
    sql = "SELECT id, nome FROM categorias"
    if not include_inactive:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY nome"
    df = query_df(sql)
    return {f"{r['nome']} (#{int(r['id'])})": int(r["id"]) for _, r in df.iterrows()}


def supplier_options(include_inactive=False):
    sql = "SELECT id, nome FROM fornecedores"
    if not include_inactive:
        sql += " WHERE ativo = 1"
    sql += " ORDER BY nome"
    df = query_df(sql)
    return {f"{r['nome']} (#{int(r['id'])})": int(r["id"]) for _, r in df.iterrows()}


def option_label_from_id(options, row_id):
    if row_id is None:
        return "Nenhum"
    for label, opt_id in options.items():
        if opt_id == row_id:
            return label
    return "Nenhum"


def select_with_none(label, options, current_id=None, key=None):
    labels = ["Nenhum"] + list(options.keys())
    current_label = option_label_from_id(options, current_id)
    index = labels.index(current_label) if current_label in labels else 0
    selected = st.selectbox(label, labels, index=index, key=key)
    return None if selected == "Nenhum" else options[selected]


init_db()


# =========================================================
# CABEÇALHO
# =========================================================
st.title("🍽️ Gestão do Restaurante")
st.caption("CRUD de Categorias, Contas a Pagar, Fornecedores e Estoque")

tab_cat, tab_contas, tab_forn, tab_estoque = st.tabs(
    ["📂 Categorias", "💸 Contas a Pagar", "🚚 Fornecedores", "📦 Estoque"]
)


# =========================================================
# CATEGORIAS
# =========================================================
with tab_cat:
    st.subheader("Categorias")

    df = query_df(
        """
        SELECT
            id,
            nome AS Nome,
            tipo AS Tipo,
            descricao AS Descrição,
            CASE WHEN ativo = 1 THEN 'Ativo' ELSE 'Inativo' END AS Situação
        FROM categorias
        ORDER BY ativo DESC, nome
        """
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    acao = st.radio(
        "Ação",
        ["Cadastrar", "Editar", "Excluir"],
        horizontal=True,
        key="cat_acao",
    )

    if acao == "Cadastrar":
        with st.form("form_cat_novo", clear_on_submit=True):
            nome = st.text_input("Nome da categoria *")
            tipo = st.selectbox("Tipo", ["Despesa", "Estoque", "Ambos"])
            descricao = st.text_area("Descrição")
            ativo = st.checkbox("Ativa", value=True)
            salvar = st.form_submit_button("Cadastrar categoria", type="primary")

            if salvar:
                if not nome.strip():
                    st.error("Informe o nome da categoria.")
                else:
                    try:
                        execute(
                            """
                            INSERT INTO categorias (nome, tipo, descricao, ativo)
                            VALUES (?, ?, ?, ?)
                            """,
                            (nome.strip(), tipo, descricao.strip(), int(ativo)),
                        )
                        st.success("Categoria cadastrada.")
                        rerun()
                    except sqlite3.IntegrityError:
                        st.error("Já existe uma categoria com esse nome.")

    elif acao == "Editar":
        opcoes = category_options(include_inactive=True)
        if not opcoes:
            st.info("Cadastre uma categoria primeiro.")
        else:
            label = st.selectbox("Escolha a categoria", list(opcoes.keys()), key="cat_ed_sel")
            row = fetch_one("categorias", opcoes[label])

            with st.form("form_cat_editar"):
                nome = st.text_input("Nome da categoria *", value=row["nome"])
                tipos = ["Despesa", "Estoque", "Ambos"]
                tipo = st.selectbox(
                    "Tipo",
                    tipos,
                    index=tipos.index(row["tipo"]) if row["tipo"] in tipos else 2,
                )
                descricao = st.text_area("Descrição", value=row["descricao"] or "")
                ativo = st.checkbox("Ativa", value=bool(row["ativo"]))
                salvar = st.form_submit_button("Salvar alterações", type="primary")

                if salvar:
                    if not nome.strip():
                        st.error("Informe o nome da categoria.")
                    else:
                        try:
                            execute(
                                """
                                UPDATE categorias
                                SET nome = ?, tipo = ?, descricao = ?, ativo = ?
                                WHERE id = ?
                                """,
                                (
                                    nome.strip(),
                                    tipo,
                                    descricao.strip(),
                                    int(ativo),
                                    row["id"],
                                ),
                            )
                            st.success("Categoria atualizada.")
                            rerun()
                        except sqlite3.IntegrityError:
                            st.error("Já existe uma categoria com esse nome.")

    else:
        opcoes = category_options(include_inactive=True)
        if not opcoes:
            st.info("Não há categorias para excluir.")
        else:
            label = st.selectbox("Categoria a excluir", list(opcoes.keys()), key="cat_del_sel")
            cat_id = opcoes[label]
            st.warning(
                "Ao excluir, contas e itens de estoque que usavam esta categoria ficarão sem categoria."
            )
            confirmar = st.checkbox("Confirmo a exclusão desta categoria", key="cat_del_ok")
            if st.button("Excluir categoria", type="primary", disabled=not confirmar):
                execute("DELETE FROM categorias WHERE id = ?", (cat_id,))
                st.success("Categoria excluída.")
                rerun()


# =========================================================
# FORNECEDORES
# =========================================================
with tab_forn:
    st.subheader("Fornecedores")

    df = query_df(
        """
        SELECT
            id,
            nome AS Nome,
            documento AS "CNPJ/CPF",
            telefone AS Telefone,
            email AS E-mail,
            contato AS Contato,
            CASE WHEN ativo = 1 THEN 'Ativo' ELSE 'Inativo' END AS Situação
        FROM fornecedores
        ORDER BY ativo DESC, nome
        """
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    acao = st.radio(
        "Ação",
        ["Cadastrar", "Editar", "Excluir"],
        horizontal=True,
        key="forn_acao",
    )

    if acao == "Cadastrar":
        with st.form("form_forn_novo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome / Razão social *")
                documento = st.text_input("CNPJ/CPF")
                telefone = st.text_input("Telefone")
            with c2:
                email = st.text_input("E-mail")
                contato = st.text_input("Pessoa de contato")
                ativo = st.checkbox("Ativo", value=True)
            observacoes = st.text_area("Observações")
            salvar = st.form_submit_button("Cadastrar fornecedor", type="primary")

            if salvar:
                if not nome.strip():
                    st.error("Informe o nome do fornecedor.")
                else:
                    execute(
                        """
                        INSERT INTO fornecedores
                        (nome, documento, telefone, email, contato, observacoes, ativo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            nome.strip(),
                            documento.strip(),
                            telefone.strip(),
                            email.strip(),
                            contato.strip(),
                            observacoes.strip(),
                            int(ativo),
                        ),
                    )
                    st.success("Fornecedor cadastrado.")
                    rerun()

    elif acao == "Editar":
        opcoes = supplier_options(include_inactive=True)
        if not opcoes:
            st.info("Cadastre um fornecedor primeiro.")
        else:
            label = st.selectbox("Escolha o fornecedor", list(opcoes.keys()), key="forn_ed_sel")
            row = fetch_one("fornecedores", opcoes[label])

            with st.form("form_forn_editar"):
                c1, c2 = st.columns(2)
                with c1:
                    nome = st.text_input("Nome / Razão social *", value=row["nome"])
                    documento = st.text_input("CNPJ/CPF", value=row["documento"] or "")
                    telefone = st.text_input("Telefone", value=row["telefone"] or "")
                with c2:
                    email = st.text_input("E-mail", value=row["email"] or "")
                    contato = st.text_input("Pessoa de contato", value=row["contato"] or "")
                    ativo = st.checkbox("Ativo", value=bool(row["ativo"]))
                observacoes = st.text_area("Observações", value=row["observacoes"] or "")
                salvar = st.form_submit_button("Salvar alterações", type="primary")

                if salvar:
                    if not nome.strip():
                        st.error("Informe o nome do fornecedor.")
                    else:
                        execute(
                            """
                            UPDATE fornecedores
                            SET nome = ?, documento = ?, telefone = ?, email = ?,
                                contato = ?, observacoes = ?, ativo = ?
                            WHERE id = ?
                            """,
                            (
                                nome.strip(),
                                documento.strip(),
                                telefone.strip(),
                                email.strip(),
                                contato.strip(),
                                observacoes.strip(),
                                int(ativo),
                                row["id"],
                            ),
                        )
                        st.success("Fornecedor atualizado.")
                        rerun()

    else:
        opcoes = supplier_options(include_inactive=True)
        if not opcoes:
            st.info("Não há fornecedores para excluir.")
        else:
            label = st.selectbox("Fornecedor a excluir", list(opcoes.keys()), key="forn_del_sel")
            fornecedor_id = opcoes[label]
            st.warning(
                "Contas a pagar e itens de estoque ligados a esse fornecedor continuarão existindo, mas ficarão sem fornecedor."
            )
            confirmar = st.checkbox("Confirmo a exclusão deste fornecedor", key="forn_del_ok")
            if st.button("Excluir fornecedor", type="primary", disabled=not confirmar):
                execute("DELETE FROM fornecedores WHERE id = ?", (fornecedor_id,))
                st.success("Fornecedor excluído.")
                rerun()


# =========================================================
# CONTAS A PAGAR
# =========================================================
with tab_contas:
    st.subheader("Contas a Pagar")

    filtros = st.columns(4)
    with filtros[0]:
        status_filtro = st.selectbox(
            "Filtrar status",
            ["Todos", "Pendente", "Pago", "Atrasado", "Cancelado"],
            key="conta_filtro_status",
        )
    with filtros[1]:
        inicio = st.date_input("Vencimento a partir de", value=None, key="conta_ini")
    with filtros[2]:
        fim = st.date_input("Vencimento até", value=None, key="conta_fim")
    with filtros[3]:
        busca = st.text_input("Buscar descrição", key="conta_busca")

    sql = """
        SELECT
            cp.id,
            cp.descricao AS Descrição,
            COALESCE(f.nome, '-') AS Fornecedor,
            COALESCE(c.nome, '-') AS Categoria,
            cp.valor AS Valor,
            cp.vencimento AS Vencimento,
            cp.status AS Status,
            COALESCE(cp.data_pagamento, '-') AS Pagamento,
            COALESCE(cp.forma_pagamento, '-') AS "Forma de pagamento"
        FROM contas_pagar cp
        LEFT JOIN fornecedores f ON f.id = cp.fornecedor_id
        LEFT JOIN categorias c ON c.id = cp.categoria_id
        WHERE 1=1
    """
    params = []

    if status_filtro != "Todos":
        sql += " AND cp.status = ?"
        params.append(status_filtro)
    if inicio:
        sql += " AND date(cp.vencimento) >= date(?)"
        params.append(inicio.isoformat())
    if fim:
        sql += " AND date(cp.vencimento) <= date(?)"
        params.append(fim.isoformat())
    if busca.strip():
        sql += " AND lower(cp.descricao) LIKE ?"
        params.append(f"%{busca.strip().lower()}%")

    sql += " ORDER BY date(cp.vencimento), cp.id DESC"
    df = query_df(sql, params)

    if not df.empty:
        df["Valor"] = df["Valor"].map(money_br)
    st.dataframe(df, use_container_width=True, hide_index=True)

    acao = st.radio(
        "Ação",
        ["Cadastrar", "Editar", "Excluir"],
        horizontal=True,
        key="conta_acao",
    )

    categorias = category_options(include_inactive=False)
    fornecedores = supplier_options(include_inactive=False)

    if acao == "Cadastrar":
        with st.form("form_conta_nova", clear_on_submit=True):
            descricao = st.text_input("Descrição *")

            c1, c2 = st.columns(2)
            with c1:
                fornecedor_id = select_with_none(
                    "Fornecedor", fornecedores, key="conta_novo_forn"
                )
                categoria_id = select_with_none(
                    "Categoria", categorias, key="conta_novo_cat"
                )
                valor = st.number_input(
                    "Valor (R$) *", min_value=0.0, step=0.01, format="%.2f"
                )
            with c2:
                vencimento = st.date_input("Vencimento *", value=date.today())
                status = st.selectbox(
                    "Status", ["Pendente", "Pago", "Atrasado", "Cancelado"]
                )
                forma_pagamento = st.selectbox(
                    "Forma de pagamento",
                    ["", "Pix", "Dinheiro", "Cartão", "Boleto", "Transferência", "Outro"],
                )

            data_pagamento = None
            if status == "Pago":
                data_pagamento = st.date_input("Data do pagamento", value=date.today())

            observacoes = st.text_area("Observações")
            salvar = st.form_submit_button("Cadastrar conta", type="primary")

            if salvar:
                if not descricao.strip():
                    st.error("Informe a descrição.")
                elif valor <= 0:
                    st.error("O valor deve ser maior que zero.")
                else:
                    execute(
                        """
                        INSERT INTO contas_pagar
                        (descricao, fornecedor_id, categoria_id, valor, vencimento,
                         status, data_pagamento, forma_pagamento, observacoes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            descricao.strip(),
                            fornecedor_id,
                            categoria_id,
                            float(valor),
                            vencimento.isoformat(),
                            status,
                            data_pagamento.isoformat() if data_pagamento else None,
                            forma_pagamento or None,
                            observacoes.strip(),
                        ),
                    )
                    st.success("Conta cadastrada.")
                    rerun()

    elif acao == "Editar":
        contas = query_df(
            """
            SELECT id, descricao, vencimento, valor
            FROM contas_pagar
            ORDER BY date(vencimento) DESC, id DESC
            """
        )
        if contas.empty:
            st.info("Não há contas cadastradas.")
        else:
            opcoes = {
                f"#{int(r['id'])} - {r['descricao']} - {money_br(r['valor'])} - {r['vencimento']}": int(r["id"])
                for _, r in contas.iterrows()
            }
            label = st.selectbox("Escolha a conta", list(opcoes.keys()), key="conta_ed_sel")
            row = fetch_one("contas_pagar", opcoes[label])

            with st.form("form_conta_editar"):
                descricao = st.text_input("Descrição *", value=row["descricao"])

                c1, c2 = st.columns(2)
                with c1:
                    fornecedor_id = select_with_none(
                        "Fornecedor",
                        supplier_options(include_inactive=True),
                        current_id=row["fornecedor_id"],
                        key="conta_ed_forn",
                    )
                    categoria_id = select_with_none(
                        "Categoria",
                        category_options(include_inactive=True),
                        current_id=row["categoria_id"],
                        key="conta_ed_cat",
                    )
                    valor = st.number_input(
                        "Valor (R$) *",
                        min_value=0.0,
                        value=float(row["valor"]),
                        step=0.01,
                        format="%.2f",
                    )
                with c2:
                    vencimento = st.date_input(
                        "Vencimento *", value=date.fromisoformat(row["vencimento"])
                    )
                    statuses = ["Pendente", "Pago", "Atrasado", "Cancelado"]
                    status = st.selectbox(
                        "Status",
                        statuses,
                        index=statuses.index(row["status"])
                        if row["status"] in statuses
                        else 0,
                    )
                    formas = [
                        "",
                        "Pix",
                        "Dinheiro",
                        "Cartão",
                        "Boleto",
                        "Transferência",
                        "Outro",
                    ]
                    atual = row["forma_pagamento"] or ""
                    forma_pagamento = st.selectbox(
                        "Forma de pagamento",
                        formas,
                        index=formas.index(atual) if atual in formas else 0,
                    )

                data_atual = (
                    date.fromisoformat(row["data_pagamento"])
                    if row["data_pagamento"]
                    else date.today()
                )
                usar_data_pag = st.checkbox(
                    "Registrar data de pagamento",
                    value=bool(row["data_pagamento"]) or status == "Pago",
                )
                data_pagamento = (
                    st.date_input("Data do pagamento", value=data_atual)
                    if usar_data_pag
                    else None
                )

                observacoes = st.text_area(
                    "Observações", value=row["observacoes"] or ""
                )
                salvar = st.form_submit_button("Salvar alterações", type="primary")

                if salvar:
                    if not descricao.strip():
                        st.error("Informe a descrição.")
                    elif valor <= 0:
                        st.error("O valor deve ser maior que zero.")
                    else:
                        execute(
                            """
                            UPDATE contas_pagar
                            SET descricao = ?, fornecedor_id = ?, categoria_id = ?,
                                valor = ?, vencimento = ?, status = ?, data_pagamento = ?,
                                forma_pagamento = ?, observacoes = ?
                            WHERE id = ?
                            """,
                            (
                                descricao.strip(),
                                fornecedor_id,
                                categoria_id,
                                float(valor),
                                vencimento.isoformat(),
                                status,
                                data_pagamento.isoformat() if data_pagamento else None,
                                forma_pagamento or None,
                                observacoes.strip(),
                                row["id"],
                            ),
                        )
                        st.success("Conta atualizada.")
                        rerun()

    else:
        contas = query_df(
            "SELECT id, descricao, valor, vencimento FROM contas_pagar ORDER BY id DESC"
        )
        if contas.empty:
            st.info("Não há contas para excluir.")
        else:
            opcoes = {
                f"#{int(r['id'])} - {r['descricao']} - {money_br(r['valor'])} - {r['vencimento']}": int(r["id"])
                for _, r in contas.iterrows()
            }
            label = st.selectbox("Conta a excluir", list(opcoes.keys()), key="conta_del_sel")
            conta_id = opcoes[label]
            confirmar = st.checkbox("Confirmo a exclusão desta conta", key="conta_del_ok")
            if st.button("Excluir conta", type="primary", disabled=not confirmar):
                execute("DELETE FROM contas_pagar WHERE id = ?", (conta_id,))
                st.success("Conta excluída.")
                rerun()


# =========================================================
# ESTOQUE
# =========================================================
with tab_estoque:
    st.subheader("Estoque")

    c1, c2, c3 = st.columns(3)
    with c1:
        somente_ativos = st.checkbox("Somente ativos", value=True)
    with c2:
        somente_baixo = st.checkbox("Somente estoque baixo", value=False)
    with c3:
        busca_est = st.text_input("Buscar item", key="estoque_busca")

    sql = """
        SELECT
            e.id,
            e.nome AS Item,
            COALESCE(e.sku, '-') AS SKU,
            COALESCE(c.nome, '-') AS Categoria,
            COALESCE(f.nome, '-') AS Fornecedor,
            e.unidade AS Unidade,
            e.quantidade AS Quantidade,
            e.estoque_minimo AS "Estoque mínimo",
            e.custo_medio AS "Custo médio",
            (e.quantidade * e.custo_medio) AS "Valor em estoque",
            CASE
                WHEN e.quantidade <= e.estoque_minimo THEN 'BAIXO'
                ELSE 'OK'
            END AS Nível,
            CASE WHEN e.ativo = 1 THEN 'Ativo' ELSE 'Inativo' END AS Situação
        FROM estoque e
        LEFT JOIN categorias c ON c.id = e.categoria_id
        LEFT JOIN fornecedores f ON f.id = e.fornecedor_id
        WHERE 1=1
    """
    params = []
    if somente_ativos:
        sql += " AND e.ativo = 1"
    if somente_baixo:
        sql += " AND e.quantidade <= e.estoque_minimo"
    if busca_est.strip():
        sql += " AND lower(e.nome) LIKE ?"
        params.append(f"%{busca_est.strip().lower()}%")
    sql += " ORDER BY e.ativo DESC, e.nome"

    df = query_df(sql, params)
    if not df.empty:
        df["Custo médio"] = df["Custo médio"].map(money_br)
        df["Valor em estoque"] = df["Valor em estoque"].map(money_br)
    st.dataframe(df, use_container_width=True, hide_index=True)

    acao = st.radio(
        "Ação",
        ["Cadastrar", "Editar", "Excluir"],
        horizontal=True,
        key="estoque_acao",
    )

    if acao == "Cadastrar":
        with st.form("form_estoque_novo", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nome = st.text_input("Nome do item *")
                sku = st.text_input("SKU / Código")
                categoria_id = select_with_none(
                    "Categoria", category_options(), key="est_novo_cat"
                )
                fornecedor_id = select_with_none(
                    "Fornecedor", supplier_options(), key="est_novo_forn"
                )
                unidade = st.selectbox(
                    "Unidade",
                    ["un", "kg", "g", "L", "ml", "caixa", "pacote", "fardo", "outro"],
                )
            with c2:
                quantidade = st.number_input(
                    "Quantidade atual", min_value=0.0, step=0.01, format="%.2f"
                )
                estoque_minimo = st.number_input(
                    "Estoque mínimo", min_value=0.0, step=0.01, format="%.2f"
                )
                custo_medio = st.number_input(
                    "Custo médio (R$)", min_value=0.0, step=0.01, format="%.2f"
                )
                localizacao = st.text_input("Localização")
                ativo = st.checkbox("Ativo", value=True)

            observacoes = st.text_area("Observações")
            salvar = st.form_submit_button("Cadastrar item", type="primary")

            if salvar:
                if not nome.strip():
                    st.error("Informe o nome do item.")
                else:
                    execute(
                        """
                        INSERT INTO estoque
                        (nome, sku, categoria_id, fornecedor_id, unidade, quantidade,
                         estoque_minimo, custo_medio, localizacao, observacoes, ativo,
                         atualizado_em)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            nome.strip(),
                            sku.strip() or None,
                            categoria_id,
                            fornecedor_id,
                            unidade,
                            float(quantidade),
                            float(estoque_minimo),
                            float(custo_medio),
                            localizacao.strip(),
                            observacoes.strip(),
                            int(ativo),
                            datetime.now().isoformat(timespec="seconds"),
                        ),
                    )
                    st.success("Item cadastrado.")
                    rerun()

    elif acao == "Editar":
        itens = query_df("SELECT id, nome, quantidade, unidade FROM estoque ORDER BY nome")
        if itens.empty:
            st.info("Não há itens cadastrados.")
        else:
            opcoes = {
                f"#{int(r['id'])} - {r['nome']} ({r['quantidade']} {r['unidade']})": int(r["id"])
                for _, r in itens.iterrows()
            }
            label = st.selectbox("Escolha o item", list(opcoes.keys()), key="est_ed_sel")
            row = fetch_one("estoque", opcoes[label])

            with st.form("form_estoque_editar"):
                c1, c2 = st.columns(2)
                with c1:
                    nome = st.text_input("Nome do item *", value=row["nome"])
                    sku = st.text_input("SKU / Código", value=row["sku"] or "")
                    categoria_id = select_with_none(
                        "Categoria",
                        category_options(include_inactive=True),
                        current_id=row["categoria_id"],
                        key="est_ed_cat",
                    )
                    fornecedor_id = select_with_none(
                        "Fornecedor",
                        supplier_options(include_inactive=True),
                        current_id=row["fornecedor_id"],
                        key="est_ed_forn",
                    )
                    unidades = [
                        "un",
                        "kg",
                        "g",
                        "L",
                        "ml",
                        "caixa",
                        "pacote",
                        "fardo",
                        "outro",
                    ]
                    unidade = st.selectbox(
                        "Unidade",
                        unidades,
                        index=unidades.index(row["unidade"])
                        if row["unidade"] in unidades
                        else 0,
                    )
                with c2:
                    quantidade = st.number_input(
                        "Quantidade atual",
                        min_value=0.0,
                        value=float(row["quantidade"]),
                        step=0.01,
                        format="%.2f",
                    )
                    estoque_minimo = st.number_input(
                        "Estoque mínimo",
                        min_value=0.0,
                        value=float(row["estoque_minimo"]),
                        step=0.01,
                        format="%.2f",
                    )
                    custo_medio = st.number_input(
                        "Custo médio (R$)",
                        min_value=0.0,
                        value=float(row["custo_medio"]),
                        step=0.01,
                        format="%.2f",
                    )
                    localizacao = st.text_input(
                        "Localização", value=row["localizacao"] or ""
                    )
                    ativo = st.checkbox("Ativo", value=bool(row["ativo"]))

                observacoes = st.text_area(
                    "Observações", value=row["observacoes"] or ""
                )
                salvar = st.form_submit_button("Salvar alterações", type="primary")

                if salvar:
                    if not nome.strip():
                        st.error("Informe o nome do item.")
                    else:
                        execute(
                            """
                            UPDATE estoque
                            SET nome = ?, sku = ?, categoria_id = ?, fornecedor_id = ?,
                                unidade = ?, quantidade = ?, estoque_minimo = ?,
                                custo_medio = ?, localizacao = ?, observacoes = ?,
                                ativo = ?, atualizado_em = ?
                            WHERE id = ?
                            """,
                            (
                                nome.strip(),
                                sku.strip() or None,
                                categoria_id,
                                fornecedor_id,
                                unidade,
                                float(quantidade),
                                float(estoque_minimo),
                                float(custo_medio),
                                localizacao.strip(),
                                observacoes.strip(),
                                int(ativo),
                                datetime.now().isoformat(timespec="seconds"),
                                row["id"],
                            ),
                        )
                        st.success("Item atualizado.")
                        rerun()

    else:
        itens = query_df("SELECT id, nome, quantidade, unidade FROM estoque ORDER BY nome")
        if itens.empty:
            st.info("Não há itens para excluir.")
        else:
            opcoes = {
                f"#{int(r['id'])} - {r['nome']} ({r['quantidade']} {r['unidade']})": int(r["id"])
                for _, r in itens.iterrows()
            }
            label = st.selectbox("Item a excluir", list(opcoes.keys()), key="est_del_sel")
            item_id = opcoes[label]
            confirmar = st.checkbox("Confirmo a exclusão deste item", key="est_del_ok")
            if st.button("Excluir item", type="primary", disabled=not confirmar):
                execute("DELETE FROM estoque WHERE id = ?", (item_id,))
                st.success("Item excluído.")
                rerun()


# =========================================================
# RODAPÉ
# =========================================================
st.divider()
st.caption(
    "Banco local: restaurante.db • Para executar: streamlit run app.py"
)
