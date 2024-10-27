from huggingface_hub import login
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Аутентификация через токен
user_token = 'YOUR_TOKEN'
login(user_token)

# Загрузка модели и токенизатора
model_identifier = "meta-llama/Prompt-Guard-86M"
tokenizer = AutoTokenizer.from_pretrained(model_identifier)
classification_model = AutoModelForSequenceClassification.from_pretrained(model_identifier)

def detect_injection(input_text):
    """
    Проверяет, содержит ли текст SQL-инъекцию.
    
    Параметры:
    input_text (str): Текст для проверки на наличие SQL-инъекции.
    
    Возвращает:
    bool: True, если найдена инъекция, иначе False.
    """
    # Токенизация входного текста
    encoded_inputs = tokenizer(input_text, return_tensors="pt")
    
    # Получение предсказаний модели
    with torch.no_grad():
        output_logits = classification_model(**encoded_inputs).logits
    
    # Определение класса предсказания
    predicted_class = output_logits.argmax().item()
    prediction_label = classification_model.config.id2label[predicted_class]
    
    # Возвращает True, если обнаружена инъекция, иначе False
    return True if prediction_label == 'INJECTION' else False
