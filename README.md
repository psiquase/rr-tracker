# ◆ RE-RECORDING TRACKER — WEB EDITION

Sistema de controle de regravaçôes com visual **pixel-art game UI**.  
Hospedado 100% **grátis** no [Render.com](https://render.com) via GitHub.

---

## 🚀 DEPLOY EM 5 PASSOS (GitHub + Render)

### PASSO 1 — Criar repositório no GitHub

1. Acesse **https://github.com/new**
2. Nome do repo: `rr-tracker` (ou qualquer nome)
3. Visibilidade: **Public** *(necessário para o plano grátis do Render)*
4. Clique em **Create repository**

---

### PASSO 2 — Fazer upload dos arquivos

Opção A — Via terminal (recomendado):

```bash
# Dentro da pasta do projeto
git init
git add .
git commit -m "feat: initial commit — RR Tracker"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/rr-tracker.git
git push -u origin main
```

Opção B — Via interface do GitHub:
1. Na página do repo → clique em **"uploading an existing file"**
2. Arraste todos os arquivos e pastas
3. Clique em **Commit changes**

---

### PASSO 3 — Criar conta no Render

1. Acesse **https://render.com**
2. Clique em **Get Started for Free**
3. Faça login com sua conta **GitHub** (recomendado — integração automática)

---

### PASSO 4 — Criar o Web Service

1. No dashboard do Render → clique em **"New +"** → **"Web Service"**
2. Clique em **"Connect a repository"**
3. Selecione seu repositório `rr-tracker`
4. Configure assim:

| Campo           | Valor                                      |
|-----------------|--------------------------------------------|
| **Name**        | `rr-tracker`                               |
| **Region**      | `Oregon (US West)` ou o mais próximo       |
| **Branch**      | `main`                                     |
| **Runtime**     | `Python 3`                                 |
| **Build Command** | `pip install -r requirements.txt`        |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT`  |

5. Em **Instance Type** → selecione **Free**
6. Clique em **"Create Web Service"**

---

### PASSO 5 — Adicionar Persistent Disk (salvar os dados)

> ⚠️ Sem o disco, os dados são apagados a cada redeploy!

1. No painel do seu serviço → vá em **"Disks"** (menu lateral)
2. Clique em **"Add Disk"**
3. Configure:

| Campo          | Valor          |
|----------------|----------------|
| **Name**       | `rr-data`      |
| **Mount Path** | `/opt/render/project/src/data` |
| **Size**       | `1 GB` (grátis) |

4. Clique em **"Save"** — o deploy vai reiniciar automaticamente

---

## ✅ Pronto!

Após o build (1–2 min), seu app vai estar em:

```
https://rr-tracker.onrender.com
```
*(o nome pode variar — Render gera a URL automaticamente)*

---

## 🔄 Atualizar o App

Qualquer `git push` para o branch `main` faz o Render redeployar automaticamente:

```bash
git add .
git commit -m "update: nova funcionalidade"
git push
```

---

## 📁 Estrutura de arquivos

```
rr-tracker/
├── app.py              ← Flask backend + rotas + banco de dados
├── requirements.txt    ← Flask + Gunicorn
├── Procfile            ← Comando de start para o Render
├── render.yaml         ← Configuração automática do Render
├── .gitignore
├── templates/
│   ├── base.html       ← Layout base com sidebar pixel-art
│   ├── dashboard.html  ← Dashboard com Chart.js
│   ├── register.html   ← Formulário de registro
│   └── reports.html    ← Relatório semanal com tabela
└── static/
    └── css/
        └── style.css   ← CSS pixel-art completo
```

---

## 🎮 Funcionalidades

| View | Descrição |
|------|-----------|
| **◈ Dashboard** | Cards de totais + gráficos por motivo, produtor e tendência diária |
| **✚ Registrar** | Formulário com validação; campo "Descreva" aparece só para "Outro" |
| **⚑ Relatórios** | Tabela semanal com 3 semanas selecionáveis, linhas coloridas por severidade |

---

## 🛠️ Rodar localmente

```bash
pip install flask gunicorn
python app.py
# Acesse: http://localhost:5000
```

---

## 💡 Hosts gratuitos alternativos

| Host | Link | Observação |
|------|------|------------|
| **Render** ⭐ | render.com | Melhor opção, suporte a disco persistente |
| **Railway** | railway.app | $5 crédito grátis/mês |
| **Fly.io** | fly.io | 3 VMs grátis, ótimo desempenho |
| **PythonAnywhere** | pythonanywhere.com | Plano grátis com 1 app web |

---

## ⚠️ Aviso sobre o plano grátis do Render

- O serviço **hiberna após 15 min** sem acesso (cold start ~30s na próxima visita)
- Para manter sempre ativo: configure um cron job externo para "pingar" `/health` a cada 10 min (ex: [cron-job.org](https://cron-job.org))

---

*100% free · open source · offline-capable · Flask · SQLite · Chart.js*
