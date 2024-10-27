import nltk
import streamlit as st
import streamlit_authenticator as stauth
from streamlit_option_menu import option_menu

from pages_ import logins
from pages_ import mistakes
from services.logins_service import LoginsService


nltk.download('stopwords')
nltk.download('wordnet')


def main():
    st.set_page_config(page_title="СИЛА", layout="wide", page_icon="⚡")

    # if "credentials" not in st.session_state:
    #     logins_service = LoginsService()
    #     st.session_state.credentials = logins_service.credentials()
    #
    # authenticator = stauth.Authenticate(
    #     credentials=st.session_state.credentials,
    #     cookie_name="cookies_name",
    #     cookie_key="cookies_key",
    #     cookie_expiry_days=30.0
    # )
    #
    # name, state, username = authenticator.login()
    #
    # if state:
    #     # if "rerun" not in st.session_state:
    #     #     st.session_state.rerun = True
    #     #     st.rerun()
    #
    #     name = st.session_state.credentials['usernames'][username]['name']x
    name = "admin"

    with st.sidebar:

        options = [
            "Основные вопросы"
        ]
        icons = [
            "bi bi-activity"
        ]

        selected = option_menu(
            menu_title="Аналитика",
            options=options,
            icons=icons
        )

        st.subheader(f"Быстрый ответ:")
        messages = st.container(height=485)
        if prompt := st.chat_input("Напишите вопрос"):
            messages.chat_message("user").write(prompt)
            messages.chat_message("assistant").write(f"Бот: {prompt}")
        on = st.toggle("Режим генерации анекдотов")
        #if on:
            # st.write("Генерация анекдотов: вкл")
    if selected == "Основные вопросы":
        mistakes.app()

    # elif st.session_state["authentication_status"] is False:
    #     st.error('Username/password is incorrect')
    #
    # elif st.session_state["authentication_status"] is None:
    #     st.warning('Please enter your username and password')


if __name__ == "__main__":
    main()
