import flet as ft


def create_appbar(page, *args, **kwargs):
    page.appbar = ft.AppBar(
        title=ft.Text("Solitaire Atelier"),
        bgcolor="#10291D",
    )
