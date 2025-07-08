from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import yaml
from datetime import datetime
import getpass

# Pedir credenciais ao utilizador
print("Introduza as credenciais de acesso:")
username = input("Username: ")
password = getpass.getpass("Password: ")

# Pedir as datas de pesquisa
print("Introduza o intervalo de datas para a pesquisa:")
def get_valid_date(prompt):
    while True:
        date_str = input(prompt)
        try:
            date_obj = datetime.strptime(date_str, "%d-%m-%Y")
            return date_obj.strftime("%d-%m-%Y")
        except ValueError:
            print("Formato inválido. Por favor, use DD-MM-YYYY.")

start_date = get_valid_date("Inicio (DD-MM-YYYY): ")
end_date = get_valid_date("Fim (DD-MM-YYYY): ")

# Iniciar ChromeDriver
print("A iniciar o ChromeDriver...")
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 30)

time.sleep(20)  # Esperar para garantir que o ChromeDriver está pronto

driver.get("https://rentev.min-saude.pt/RENTEV/login.jsp")
try:
    # Login
    print("A iniciar sessão")
    wait.until(EC.presence_of_element_located((By.NAME, "j_username")))
    driver.find_element(By.NAME, "j_username").send_keys(username)
    driver.find_element(By.NAME, "j_password").send_keys(password)
    driver.find_element(By.XPATH, "//input[@value='AVANÇAR']").click()

    # Filtrar os resultados
    print("A aplicar os filtros de pesquisa")
    wait.until(EC.presence_of_element_located((By.ID, "p_DataCriacao_de")))
    driver.find_element(By.ID, "p_DataCriacao_de").clear()
    driver.find_element(By.ID, "p_DataCriacao_de").send_keys(start_date)
    driver.find_element(By.ID, "p_DataCriacao_a").clear()
    driver.find_element(By.ID, "p_DataCriacao_a").send_keys(end_date)
    select_estado = Select(driver.find_element(By.ID, "p_estado"))
    select_estado.select_by_value("A")
    pesquisar_button = driver.find_element(By.XPATH, "//input[@value='PESQUISAR']")
    pesquisar_button.click()

    # Aguardar até que pelo menos uma linha de resultado esteja presente
    wait.until(EC.presence_of_element_located((By.XPATH, "//table[@id='results']/tbody/tr")))

    # Gravar dados
    print("A guardar os dados")
    try:
        total_pages_elem = driver.find_element(By.ID, "totalPaginas")
        total_pages_value = total_pages_elem.get_attribute("value")
        total_pages = int(total_pages_value)
    except Exception as e:
        print(f"Erro ao obter o número total de páginas: {e}")

    data = []
    for page in range(total_pages):
        print(f"A analisar página: {page + 1}/{total_pages}")

        rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table[@id='results']/tbody/tr")))

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 8:
                sns_input = cells[0].find_elements(By.TAG_NAME, "input")
                sns_value = sns_input[0].get_attribute("value") if sns_input else ""
                sns_text = cells[0].text.strip()
                data.append({
                    "SNS": sns_text,
                    "SNS_ID": sns_value,
                    "Nome": cells[1].text.strip(),
                    "Data Criacao": cells[2].text.strip(),
                    "Estado": cells[3].text.strip().split("\n")[0],
                    "Tipo Doc": cells[4].text.strip(),
                    "Num Doc": cells[5].text.strip(),
                    "Instituicao": cells[6].text.strip(),
                    "Responsavel": cells[7].text.strip()
                })

        if page < total_pages - 1:
            next_button = driver.find_element(By.ID, "navNext")
            if next_button.is_enabled() and "btnNext-disabled" not in next_button.get_attribute("class"):
                first_row_id = rows[0].get_attribute("id")
                next_button.click()
                wait.until(lambda d: d.find_elements(By.XPATH, "//table[@id='results']/tbody/tr")[0].get_attribute("id") != first_row_id)
            else:
                print("Botão 'Próxima' desabilitado ou não encontrado. A parar a navegação.")
                break

    df = pd.DataFrame(data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"rentev_data_{timestamp}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"Dados guardados em {filename}")
except Exception as e:
    print(f"Ocorreu um erro: {e}")
finally:
    driver.quit()
    input("Pressione Enter para sair...")