# -*- coding: utf-8 -*-
"""
Daniel Trader PRO - Bot Multi-Estratégias
Versão ajustada para PythonAnywhere e horários UTC
Terminal com cores, banners, martingale, stop gain/stop loss e ciclos programados
"""

from iqoptionapi.stable_api import IQ_Option
from datetime import datetime, timedelta
import time, sys, pandas as pd, os, csv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ------------------- CONFIGURAÇÕES -------------------
EMAIL = "danielpissika07@gmail.com"
SENHA = "011020dM@2"
CONTA = "PRACTICE"  # PRACTICE ou REAL
ATIVO = "EURUSD-OTC"
VALOR_ENTRADA = 5
TIMEFRAME = 1
TIPO = "binaria"  # digital ou binaria
STOP_GAIN = 15
STOP_LOSS = 2000
MARTINGALE = 10
QTD_VELAS = 5

# Ciclos de operação em UTC
CICLOS_UTC = ["12:01", "12:09", "13:39", "19:21"]

# ---------------- CONFIGURAÇÕES EMAIL ----------------
EMAIL_REMETENTE = "botdanieltrader@gmail.com"
SENHA_EMAIL = "xxaw imli czug osso"
EMAIL_DESTINO = "maiaraeeu2017@gmail.com"

# ---------------- cores ----------------
class Cores:
    RESET="\033[0m"
    RED="\033[91m"
    GREEN="\033[92m"
    YELLOW="\033[93m"
    BLUE="\033[94m"
    MAGENTA="\033[95m"
    CYAN="\033[96m"
    WHITE="\033[97m"

# ---------------- util ----------------
def cls():
    os.system("cls" if os.name=="nt" else "clear")

def mostrar_banner():
    cls()
    print(f"{Cores.CYAN}{'='*60}{Cores.RESET}")
    print(f"{Cores.MAGENTA}{'BEM VINDO AO DANIEL TRADER PRO':^60}{Cores.RESET}")
    print(f"{Cores.YELLOW}{'BOT MULTI-ESTRATÉGIAS (UTC)':^60}{Cores.RESET}")
    print(f"{Cores.CYAN}{'='*60}{Cores.RESET}\n")

def agora_utc():
    return datetime.utcnow()

# ---------------- conexão ----------------
def conectar(email, senha, tipoConta='PRACTICE'):
    api = IQ_Option(email, senha)
    print("Conectando...")
    api.connect()
    t0=time.time()
    while not api.check_connect() and (time.time()-t0)<10:
        time.sleep(0.5)
    if not api.check_connect():
        print(f"{Cores.RED}[ERRO] Não foi possível conectar.{Cores.RESET}")
        sys.exit()
    api.change_balance(tipoConta)
    print(f"{Cores.GREEN}[OK] Conectado. Conta: {tipoConta}{Cores.RESET}")
    return api

# ---------------- salvar relatório ----------------
def salvar_relatorio(dados):
    data_hoje = agora_utc().strftime("%Y-%m-%d")
    arquivo = os.path.join(os.getcwd(), f"relatorio_{data_hoje}.csv")
    file_exists = os.path.isfile(arquivo)
    with open(arquivo, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Data/Hora UTC", "Ativo", "Direção", "Entrada", "Resultado", "Lucro acumulado"])
        writer.writerow(dados)

# ---------------- enviar relatório por email ----------------
def enviar_email_relatorio(arquivo_csv):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINO
        msg['Subject'] = f"Relatório diário do Daniel Trader - {agora_utc().strftime('%Y-%m-%d')}"
        corpo = MIMEText("Segue o relatório diário do Daniel Trader PRO em anexo.", "plain")
        msg.attach(corpo)
        anexo = open(arquivo_csv, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(anexo.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename= {arquivo_csv}')
        msg.attach(part)
        anexo.close()
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_REMETENTE, SENHA_EMAIL)
        server.sendmail(EMAIL_REMETENTE, EMAIL_DESTINO, msg.as_string())
        server.quit()
        print(f"{Cores.GREEN}[EMAIL] Relatório enviado para {EMAIL_DESTINO}{Cores.RESET}")
    except Exception as e:
        print(f"{Cores.RED}[EMAIL] Erro ao enviar relatório: {e}{Cores.RESET}")

# ---------------- funções trading ----------------
def payout_for(par, tipo, api, timeframe=1):
    try:
        if tipo=='turbo':
            all_profit=api.get_all_profit()
            if par in all_profit: return float(all_profit[par]['turbo'])*100
            return 0
        else:
            api.subscribe_strike_list(par,timeframe)
            t0=time.time()
            while True:
                d=api.get_digital_current_profit(par,timeframe)
                if d not in (False,None):
                    api.unsubscribe_strike_list(par,timeframe)
                    return float(d)
                if time.time()-t0>10:
                    api.unsubscribe_strike_list(par,timeframe)
                    return 0
                time.sleep(0.3)
    except: return 0

def compra(api,ativo,valor,direcao,exp,tipo):
    try:
        if tipo=='digital':
            try: ok,id_=api.buy_digital_spot_v2(ativo,valor,direcao,exp)
            except: ok,id_=api.buy_digital_spot(ativo,valor,direcao,exp)
        else: ok,id_=api.buy(valor,ativo,direcao,exp)
        return ok,id_
    except: return False,None

def check_result(api,order_id,tipo):
    t0=time.time()
    while True:
        try:
            if tipo=='digital': status,resultado=api.check_win_digital_v2(order_id)
            else: status,resultado=api.check_win_v4(order_id)
        except: status,resultado=False,None
        if status: return resultado
        if time.time()-t0>180:
            return None
        time.sleep(0.5)

def Martingale(entrada,payout):
    if payout<=0: return entrada
    return round(entrada*(1+payout)/payout,2)

# ---------------- estratégias ----------------
def estrategia_tres_soldados(cores): return 'call' if cores.count('A')>=3 else ''
def estrategia_tres_corvos(cores): return 'put' if cores.count('B')>=3 else ''
def estrategia_force_of_two(cores): return 'call' if cores[-2:] == ['A','A'] else 'put' if cores[-2:] == ['B','B'] else ''
def estrategia_cruzamento_medias(api,ativo,timeframe,periodo1=5,periodo2=10):
    velas=api.get_candles(ativo,timeframe*60,periodo2+1,time.time())
    df=pd.DataFrame(velas)
    EMA1=df['close'].ewm(span=periodo1,adjust=False).mean().iloc[-1]
    EMA2=df['close'].ewm(span=periodo2,adjust=False).mean().iloc[-1]
    return 'call' if EMA1>EMA2 else 'put' if EMA2>EMA1 else ''

# ---------------- stop e ciclos ----------------
def stop_check(lucro_local,gain,loss):
    if lucro_local<=-abs(loss):
        print(f"{Cores.RED}[STOP LOSS] atingido! Bot encerrado.{Cores.RESET}")
        return False
    if lucro_local>=abs(gain):
        print(f"{Cores.GREEN}[STOP GAIN] atingido! Bot encerrado.{Cores.RESET}")
        return False
    return True

def proximo_ciclo_utc(ciclos=CICLOS_UTC):
    agora_atual = agora_utc()
    futuros = []
    for ciclo in ciclos:
        hora, minuto = map(int, ciclo.split(":"))
        inicio = agora_atual.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        if inicio > agora_atual:
            futuros.append(inicio)
    if futuros:
        return futuros[0]
    else:
        amanha = agora_atual + timedelta(days=1)
        hora, minuto = map(int, ciclos[0].split(":"))
        inicio = amanha.replace(hour=hora, minute=minuto, second=0, microsecond=0)
        return inicio

# ---------------- execução ----------------
mostrar_banner()
API = conectar(EMAIL, SENHA, CONTA)
martingale = MARTINGALE
lucro = 0
historico=[]

# Espera até o próximo ciclo em UTC
inicio_ciclo = proximo_ciclo_utc()
print(f"⏳ Aguardando próximo ciclo UTC: {inicio_ciclo.strftime('%H:%M')}")
while agora_utc() < inicio_ciclo:
    time.sleep(10)

# ---------------- loop principal ----------------
try:
    rodando = True
    while rodando:
        if not stop_check(lucro, STOP_GAIN, STOP_LOSS):
            break

        print("\r[Aguardando oportunidade...]", end="")
        time.sleep(1)

        velas = API.get_candles(ATIVO, TIMEFRAME*60, QTD_VELAS, time.time())
        cores = ['A' if v['open'] < v['close'] else 'B' if v['open'] > v['close'] else 'D' for v in velas]

        direcao1 = estrategia_tres_soldados(cores)
        direcao2 = estrategia_tres_corvos(cores)
        direcao3 = estrategia_force_of_two(cores)
        direcao4 = estrategia_cruzamento_medias(API, ATIVO, TIMEFRAME)
        direcao = direcao1 or direcao2 or direcao3 or direcao4
        if not direcao:
            continue

        valor_entrada_atual = VALOR_ENTRADA
        payout = payout_for(ATIVO, 'digital' if TIPO=="digital" else 'turbo', API, TIMEFRAME)
        if payout == 0:
            print("⚠️ Payout zero, pulando operação")
            continue
        payout_decimal = payout / 100.0

        # Loop do Martingale
        for i_gale in range(martingale+1):
            ok, order_id = compra(API, ATIVO, valor_entrada_atual, direcao, 1, 'digital' if TIPO=="digital" else 'binaria')
            if not ok:
                print("❌ Falha ao executar ordem")
                break

            print(f"{Cores.CYAN}Executando ordem...{Cores.RESET}")
            time.sleep(1)

            resultado = check_result(API, order_id, 'digital' if TIPO=="digital" else 'binaria')
            if resultado is None:
                print("⚠️ Resultado não disponível, pulando Martingale")
                continue  # Martingale só em perda real

            valor_result = float(resultado)
            lucro += round(valor_result, 2)
            status_result = "WIN" if valor_result > 0 else "LOSS" if valor_result < 0 else "EMPATE"
            cor_result = Cores.GREEN if valor_result > 0 else Cores.RED if valor_result < 0 else Cores.YELLOW
            print(f"[{agora_utc().strftime('%H:%M:%S')}] Resultado: {cor_result}{status_result}{Cores.RESET} -> {round(valor_result,2)} | Lucro acumulado: {Cores.CYAN}{round(lucro,2)}{Cores.RESET}")

            historico.append(f"{status_result} {round(valor_result,2)}")
            if len(historico) > 5:
                historico.pop(0)
            print(f"{Cores.MAGENTA}Últimas 5 operações: {historico}{Cores.RESET}")

            salvar_relatorio([
                agora_utc().strftime("%Y-%m-%d %H:%M:%S"),
                ATIVO,
                direcao,
                valor_entrada_atual,
                status_result,
                round(lucro, 2)
            ])

            # Martingale somente se perdeu
            if valor_result < 0:
                valor_entrada_atual = Martingale(valor_entrada_atual, payout_decimal)
                print(f"🔁 Aplicando Martingale, próximo valor: {valor_entrada_atual}")
            else:
                break  # se ganhou ou empatou, sai do loop do Martingale

            if not stop_check(lucro, STOP_GAIN, STOP_LOSS):
                rodando = False
                break

    print(f"\n✅ Bot encerrou automaticamente! Lucro final: {round(lucro,2)}\n")
    arquivo_relatorio = os.path.join(os.getcwd(), f"relatorio_{agora_utc().strftime('%Y-%m-%d')}.csv")
    enviar_email_relatorio(arquivo_relatorio)

except KeyboardInterrupt:
    print(f"\n{Cores.MAGENTA}Encerrado pelo usuário.{Cores.RESET}")
except Exception as e:
    print(f"{Cores.RED}[ERRO] Erro inesperado: {e}{Cores.RESET}")
finally:
    try: API.close()
    except: pass
