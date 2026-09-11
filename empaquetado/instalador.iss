; Instalador de BINGO con Inno Setup (tarea 4.14, contrato §5.11).
;
; No crea `%LOCALAPPDATA%\Bingo` (hallazgo explícito del plan): lo hace
; `asegurar_estructura()` en el primer arranque, que ya existe y ya está
; probado — duplicarlo aquí crearía dos dueños de la misma estructura, y un
; instalador que la crea con permisos distintos a los que el proceso usaría
; después es la clase de bug que solo aparece en el equipo del operador, la
; noche del evento.
;
; Compilar (con Inno Setup Compiler instalado, ISCC.exe en el PATH), DESPUÉS
; de generar `dist\bingo\` con bingo.spec:
;   iscc empaquetado\instalador.iss

#define MyAppName "BINGO"
#define MyAppPublisher "Bingo App"
#define MyAppExeName "bingo.exe"
; Sin fuente única real disponible dentro de Inno Setup (no ejecuta Python):
; se pasa por línea de comandos en el pipeline de build,
; `/DMyAppVersion=<version>` leída de `bingo.__version__` (decisión D12) —
; nunca un número escrito a mano aquí, que divergiría del que la propia app
; muestra en Ajustes.
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0-sin-version"
#endif

[Setup]
AppId={{B96C6C6A-6F5A-4E20-9B1E-2B6E7E3B6B4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Sin privilegios de administrador: el operador puede no tenerlos en el
; equipo del evento, y la app nunca escribe en Archivos de programa —
; `%LOCALAPPDATA%\Bingo` es de usuario, no de máquina.
PrivilegesRequired=lowest
OutputDir=..\dist_instalador
OutputBaseFilename=bingo-instalador-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
; `dist\bingo\` es lo que produce `bingo.spec` — todo el árbol de
; PyInstaller (el .exe y lo que necesita al lado), recursivo.
Source: "..\dist\bingo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: escritorio

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent

; El desinstalador NO toca `%LOCALAPPDATA%\Bingo` a propósito: es donde
; viven la base de datos, los respaldos y los cartones ya impresos de
; eventos reales. Desinstalar la aplicación no debe poder borrar esos datos
; sin que el operador lo pida por separado (fuera de este instalador).
