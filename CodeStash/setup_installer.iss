; =====================================================================
; InoodeTree - 微信公众号 AI 内容创作与自动发布平台
; Inno Setup 简体中文安装包打包脚本
; =====================================================================

#define MyAppName "引载树 InodeTree"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "CodeStash Team"
#define MyAppURL "https://gitee.com/drive-h/aaa-uniapp-codestash-exe-build"
#define MyAppExeName "InodeTree.exe"
#define MyCliExeName "inodetree-cli.exe"

[Setup]
; 基础应用信息
AppId={{D37E8F90-1A2B-3C4D-5E6F-7890ABCDEF12}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 默认安装目录
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; 安装包文件名与压缩算法
OutputDir=installer_output
OutputBaseFilename=InodeTree_Setup_v{#MyAppVersion}
SetupIconFile=static\logo-red.ico
Compression=lzma2/ultra64
SolidCompression=yes

; 权限与界面风格
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern

; 语言配置 (支持简体中文与英文)
[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addpath"; Description: "将命令行工具 (inodetree-cli) 添加到系统 PATH 环境变量"; GroupDescription: "高级选项:"; Flags: unchecked

[Files]
; 打包的主可执行文件与命令行工具
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\{#MyCliExeName}"; DestDir: "{app}"; Flags: ignoreversion

; 打包配置文件模版与说明文档
Source: "config.json.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

; 打包 UI 静态文件与技能资源
Source: "static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "launcher_ui\*"; DestDir: "{app}\launcher_ui"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "skills\*"; DestDir: "{app}\skills"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\static\logo-red.ico"
Name: "{group}\{#MyAppName} 命令行工具 (CLI)"; Filename: "{app}\{#MyCliExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\static\logo-red.ico"

[Run]
; 首次安装完成后提示生成配置文件 config.json
Filename: "{cmd}"; Parameters: "/c if not exist ""{app}\config.json"" copy ""{app}\config.json.example"" ""{app}\config.json"""; Flags: runhidden
; 安装完成后可选启动应用
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// 可选 PATH 环境变量写入逻辑
procedure CurStepChanged(CurStep: TSetupStep);
var
  PathVar: string;
  AppDir: string;
begin
  if (CurStep = ssPostInstall) and IsTaskSelected('addpath') then
  begin
    AppDir := ExpandConstant('{app}');
    if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'PATH', PathVar) then
    begin
      if Pos(AppDir, PathVar) = 0 then
      begin
        RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'PATH', PathVar + ';' + AppDir);
      end;
    end
    else
    begin
      RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'PATH', AppDir);
    end;
  end;
end;
