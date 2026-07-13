[Setup]
AppName=Sonic Forge
AppVersion=1.0
DefaultDirName={autopf}\Sonic Forge
DefaultGroupName=Sonic Forge
OutputDir=installer
OutputBaseFilename=SonicForgeSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=SonicForge.ico
UninstallDisplayIcon={app}\SonicForge.exe

[Files]
Source: "dist\Sonic Forge.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Sonic Forge"; Filename: "{app}\Sonic Forge.exe"
Name: "{commondesktop}\Sonic Forge"; Filename: "{app}\Sonic Forge.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\Sonic Forge.exe"; Description: "Launch Sonic Forge"; Flags: nowait postinstall skipifsilent