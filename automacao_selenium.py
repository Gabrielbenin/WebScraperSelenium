import os
import time
import random
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# ------------------------------------------------------------
# CONFIGURAÇÕES
# ------------------------------------------------------------
CSV_PATH = "links.csv"
USER_DATA_DIR = os.path.join(os.getcwd(), "BotChromeProfile")
WAIT_PAGE_LOAD = 10
WAIT_LENS_CLOSE = 25
WAIT_AFTER_INSERT = 6
COOLDOWN_MIN = 25
COOLDOWN_MAX = 45
ANTIBAN_EVERY_MIN = 25
ANTIBAN_EVERY_MAX = 40
ANTIBAN_MIN = 6 * 60
ANTIBAN_MAX = 10 * 60

# ------------------------------------------------------------
# FUNÇÕES
# ------------------------------------------------------------
def escolher_sites():
    todas = {
        "1": "mercadolivre",
        "2": "casasbahia",
        "3": "leroymerlin",
        "4": "americanas",
        "5": "amazon.com.br",
        "6": "magazineluiza",
        "7": "shopee"
    }
    print("\nEscolha os sites concorrentes (números separados por vírgula):")
    for k, v in todas.items():
        print(f"  {k} - {v}")
    escolha = input("Exemplo: 1,3,5 -> ")
    indices = [s.strip() for s in escolha.split(",") if s.strip() in todas]
    if not indices:
        print("Nenhum site escolhido, usando padrão (todos exceto Shopee).")
        indices = ["1","3","4","5","6"]  # sem casasbahia (2) e shopee (7)
    sites = [todas[i] for i in indices]
    print(f"Sites selecionados: {sites}")
    return sites

def ler_urls(csv_path):
    urls = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].strip().startswith("http"):
                urls.append(row[0].strip())
    return urls

def esperar_aba_fechar(driver, handles_antes, timeout=10):
    inicio = time.time()
    while time.time() - inicio < timeout:
        if len(driver.window_handles) < len(handles_antes):
            return True
        time.sleep(0.5)
    return False

def fechar_todas_abas_exceto_primeira(driver):
    handles = driver.window_handles
    if len(handles) <= 1:
        return 0
    primeira = handles[0]
    fechadas = 0
    for h in handles[1:]:
        try:
            driver.switch_to.window(h)
            driver.close()
            fechadas += 1
        except:
            pass
    driver.switch_to.window(primeira)
    return fechadas

def fechar_todas_abas_lens(driver):
    fechadas = 0
    for handle in driver.window_handles:
        try:
            driver.switch_to.window(handle)
            if "lens.google.com" in driver.current_url:
                driver.close()
                fechadas += 1
        except:
            continue
    if fechadas > 0:
        print(f"  Fechadas {fechadas} aba(s) do Lens.")
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
    return fechadas

def processar_abas(driver):
    time.sleep(1.5)
    handles = driver.window_handles
    if not handles:
        print("  Nenhuma aba aberta.")
        return 0
    abas_validas = []
    for h in handles:
        try:
            driver.switch_to.window(h)
            if "google.com" not in driver.current_url:
                abas_validas.append(h)
        except:
            continue
    if not abas_validas:
        print("  Nenhuma aba valida.")
        return 0
    aba_principal = abas_validas[0]
    if not aba_principal:
        print("  ERRO: Nenhuma aba de produto encontrada.")
        return 0
    outras = [h for h in abas_validas if h != aba_principal]
    driver.switch_to.window(aba_principal)
    ordem = [aba_principal] + outras
    total = len(ordem)
    print(f"  Abas a processar: {total}")
    for idx, handle in enumerate(ordem):
        for _ in range(3):
            try:
                driver.switch_to.window(handle)
                break
            except:
                time.sleep(0.5)
        else:
            print(f"  Falha na aba {idx+1}, pulando.")
            continue
        time.sleep(random.uniform(0.8, 1.2))
        try:
            if idx == total - 1:
                btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.ID, "tm-btn-salvar")))
                btn.click()
                print(f"  Aba {idx+1}/{total}: END")
            else:
                btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.ID, "tm-btn-adicionar")))
                btn.click()
                print(f"  Aba {idx+1}/{total}: INSERT")
        except Exception as e:
            print(f"  Erro ao clicar: {e}")
            try:
                if idx == total - 1:
                    driver.execute_script("document.getElementById('tm-btn-salvar')?.click();")
                else:
                    driver.execute_script("document.getElementById('tm-btn-adicionar')?.click();")
            except:
                pass
            continue
        handles_antes = driver.window_handles
        esperar_aba_fechar(driver, handles_antes, timeout=WAIT_AFTER_INSERT+2)
        time.sleep(random.uniform(0.5, 1.0))
    return total

def criar_driver():
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={USER_DATA_DIR}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-minimized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    if not driver.window_handles:
        driver.execute_script("window.open('about:blank', '_blank');")
    driver.switch_to.window(driver.window_handles[0])
    return driver

def configurar_extensoes(driver, sites_escolhidos):
    """Tenta configurar a extensão Lens via Selenium (opcional, não falha se não conseguir)."""
    try:
        driver.execute_script(f"""
            (function() {{
                if (window.__tm_lens_config && window.__tm_lens_config.setTargetSites) {{
                    window.__tm_lens_config.setTargetSites({sites_escolhidos});
                }}
            }})();
        """)
        print("  Configuração de sites enviada para extensão Lens (se ativa).")
    except Exception as e:
        print(f"  Aviso: não foi possível configurar a extensão: {e}")

def limpar_apos_produto(driver):
    try:
        fechar_todas_abas_lens(driver)
        fechadas = fechar_todas_abas_exceto_primeira(driver)
        if fechadas > 0:
            print(f"  Limpeza: {fechadas} abas extras fechadas.")
        driver.get("about:blank")
    except Exception as e:
        print(f"  Aviso na limpeza: {e}")

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    print("=== BOT CRAWLER CONCORRENTES (SELENIUM) ===")
    sites_escolhidos = escolher_sites()
    urls = ler_urls(CSV_PATH)
    if not urls:
        print(f"Nenhuma URL encontrada em {CSV_PATH}.")
        return
    print(f"Total de produtos: {len(urls)}")
    input("Pressione ENTER para começar...")
    driver = criar_driver()
    configurar_extensoes(driver, sites_escolhidos)
    produto_count = 0
    falhas_consecutivas = 0
    for url_produto in urls:
        if produto_count > 0:
            cooldown = random.randint(COOLDOWN_MIN, COOLDOWN_MAX)
            print(f"\nAguardando {cooldown}s...")
            time.sleep(cooldown)
        produto_count += 1
        print(f"\n--- Produto {produto_count}/{len(urls)}: {url_produto}")
        try:
            driver.current_url
        except (NoSuchWindowException, WebDriverException):
            print("  Driver perdido. Recriando...")
            driver.quit()
            driver = criar_driver()
        limpar_apos_produto(driver)
        driver.execute_script("window.open('');")
        nova_aba = driver.window_handles[-1]
        driver.switch_to.window(nova_aba)
        driver.get(url_produto)
        try:
            WebDriverWait(driver, WAIT_PAGE_LOAD).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        except TimeoutException:
            print(f"ERRO: timeout")
            with open("erro.log", "a", encoding="utf-8") as f:
                f.write(f"{time.ctime()} - Timeout: {url_produto}\n")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            falhas_consecutivas += 1
            if falhas_consecutivas >= 3:
                print("Três falhas. Reiniciando driver...")
                driver.quit()
                driver = criar_driver()
                falhas_consecutivas = 0
            continue
        falhas_consecutivas = 0
        driver.execute_script("if(window.__tm_lens && window.__tm_lens.start) window.__tm_lens.start();")
        print(f"  Lens disparado. Aguardando {WAIT_LENS_CLOSE}s...")
        time.sleep(WAIT_LENS_CLOSE)
        fechar_todas_abas_lens(driver)
        time.sleep(2)
        print("  Processando abas...")
        processadas = processar_abas(driver)
        print(f"  {processadas} abas processadas.")
        limpar_apos_produto(driver)
        if produto_count % random.randint(ANTIBAN_EVERY_MIN, ANTIBAN_EVERY_MAX) == 0:
            pausa = random.randint(ANTIBAN_MIN, ANTIBAN_MAX)
            minutos = pausa // 60
            print(f"\n*** PAUSA ANTI‑BAN: {minutos} minutos ***")
            time.sleep(pausa)
    print("\n=== FIM ===")
    driver.quit()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open("erro.log", "w", encoding="utf-8") as f:
            f.write(f"{time.ctime()} - ERRO FATAL: {str(e)}\n")
        print(f"\nERRO FATAL: {e}")
        input("Pressione ENTER para sair...")