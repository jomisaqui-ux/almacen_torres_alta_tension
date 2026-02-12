import os

# Configuración
DIRECTORIO_RAIZ = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_SALIDA = 'contexto_proyecto_completo.txt'

# Carpetas a ignorar (puedes agregar más)
IGNORAR_CARPETAS = {
    'venv', '.git', '__pycache__', '.idea', '.vscode', 
    'migrations', 'static', 'media', 'assets'
}

# Extensiones permitidas (solo queremos código texto)
EXTENSIONES_PERMITIDAS = {
    '.py', '.html', '.css', '.js', '.txt', '.md', '.json'
}

def es_archivo_valido(nombre_archivo):
    ext = os.path.splitext(nombre_archivo)[1].lower()
    return ext in EXTENSIONES_PERMITIDAS

def generar_contexto():
    with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as salida:
        salida.write(f"CONTEXTO DEL PROYECTO: {os.path.basename(DIRECTORIO_RAIZ)}\n")
        salida.write("="*50 + "\n\n")

        for raiz, carpetas, archivos in os.walk(DIRECTORIO_RAIZ):
            # Filtrar carpetas ignoradas para que no entre en ellas
            carpetas[:] = [d for d in carpetas if d not in IGNORAR_CARPETAS]

            for archivo in archivos:
                if es_archivo_valido(archivo) and archivo != os.path.basename(__file__) and archivo != ARCHIVO_SALIDA:
                    ruta_completa = os.path.join(raiz, archivo)
                    ruta_relativa = os.path.relpath(ruta_completa, DIRECTORIO_RAIZ)

                    try:
                        with open(ruta_completa, 'r', encoding='utf-8') as f:
                            contenido = f.read()
                            
                        # Escribir encabezado del archivo
                        salida.write(f"\n{'='*20}\n")
                        salida.write(f"ARCHIVO: {ruta_relativa}\n")
                        salida.write(f"{'='*20}\n")
                        salida.write(contenido + "\n")
                        print(f"Leído: {ruta_relativa}")
                        
                    except Exception as e:
                        print(f"Error leyendo {ruta_relativa}: {e}")

    print(f"\n✅ ¡Listo! Se ha generado el archivo '{ARCHIVO_SALIDA}'.")
    print("Ahora puedes subir este archivo a la IA.")

if __name__ == '__main__':
    generar_contexto()
