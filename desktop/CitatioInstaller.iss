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

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\Citatio.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Citatio"; Filename: "{app}\Citatio.exe"
Name: "{commondesktop}\Citatio"; Filename: "{app}\Citatio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Citatio.exe"; Description: "Launch Citatio"; Flags: nowait postinstall skipifsilent
