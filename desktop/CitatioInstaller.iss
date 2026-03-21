[Setup]
AppId={{CitatioApp}
AppName=Citatio
AppVersion={#MyAppVersion}
AppPublisher=SIMI2COOL
DefaultDirName={autopf}\Citatio
DefaultGroupName=Citatio
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=dist\svgviewer-output (3) (1).ico
UninstallDisplayIcon={app}\Citatio.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\Citatio.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\svgviewer-output (3) (1).ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Citatio"; Filename: "{app}\Citatio.exe"; IconFilename: "{app}\svgviewer-output (3) (1).ico"
; Per-user desktop only — {commondesktop} needs admin and fails with PrivilegesRequired=lowest (0x80070005).
Name: "{userdesktop}\Citatio"; Filename: "{app}\Citatio.exe"; IconFilename: "{app}\svgviewer-output (3) (1).ico"; Tasks: desktopicon

[Run]
Filename: "{app}\Citatio.exe"; Description: "Launch Citatio"; Flags: nowait postinstall skipifsilent
