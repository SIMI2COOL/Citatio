# Citatio — página de descarga (Vercel)

Esta carpeta es una **web estática de una sola página** con estilo **retro**: rayas horizontales tipo IBM (azul marino), ruido y scanlines CRT, título **CITATIO** en pixel (Press Start 2P) con brillo ámbar, ventana estilo Win95/Mac OS 9, barra arcoíris superior tipo Mac clásico, taskbar abajo con reloj, cursor flecha clásico y pitido de arranque opcional (Web Audio).

El botón **Descargar para Windows** obtiene automáticamente el último `Citatio-Setup-*.exe` desde [GitHub Releases](https://github.com/SIMI2COOL/Citatio/releases).

## Desplegar en Vercel

1. Crea una cuenta en [vercel.com](https://vercel.com) e inicia sesión con GitHub.
2. **Add New… → Project** e importa el repo **Citatio**.
3. En **Root Directory**, elige **`website`** (importante).
4. Framework: **Other** (o “No framework”). No hace falta comando de build.
5. **Deploy**.

Tu URL será algo como `https://citatio-xxxxx.vercel.app`. Puedes poner un dominio propio en **Project → Settings → Domains**.

Cada vez que publiques un **nuevo release** en GitHub con el instalador, la página seguirá enlazando a la última versión sin editar el HTML.
