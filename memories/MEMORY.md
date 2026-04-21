     1|用户有自建的个人助手Web工具，位于 /mnt/d/Users/80318604/CodeBuddy/本地个人助手/。技术栈：FastAPI + Streamlit + SQLite。启动方式：在 Windows 目录下直接运行 start.bat（会启动API服务8888端口和Streamlit 8501端口）。Windows Python路径：D:\Python\python.exe (Python 3.14.3)。
     2|§
     3|用户的本地个人助手在 Windows 文件系统上，有 start.bat 启动脚本。直接运行 start.bat 即可，不需要在 WSL 里折腾虚拟环境。
     4|§
     5|Claude Code安装在Windows端：/mnt/d/Users/80318604/.local/bin/claude.exe (v2.1.104)。认证方式：ANTHROPIC_AUTH_TOKEN，使用OPPO内部代理端点 https://oppo-cloud-llm-personal-cn.oppoer.me/personal/anthropic/api。可从WSL直接调用Windows exe。
     6|§
     7|Claude Code已安装：路径 /mnt/d/Users/80318604/.local/bin/claude.exe，版本2.1.104，使用OPPO内部代理端点(oppo-cloud-llm-personal-cn.oppoer.me)。已在~/.bashrc添加alias。
     8|§
     9|Outlook邮件发送（Windows）：通过PowerShell COM对象自动化Outlook发邮件。模式：$outlook = New-Object -ComObject Outlook.Application; $mail = $outlook.CreateItem(0); $mail.To/Subject/Body/Attachments.Add(); $mail.Display()显示窗口或.Send()直接发送。中文文件名需注意编码问题。
    10|§
    11|Hermes Workspace 部署完成。项目位置: /mnt/d/Users/80318604/hermes-workspace。启动: ~/start-hermes-workspace.sh。停止: tmux kill-session -t hermes-workspace。端口: 3000 (Workspace) + 8642 (Gateway)。IP会变化，访问前运行 `hostname -I` 确认。
    12|§
    13|Hermes Workspace IP地址可能随VPN重连变化。遇到访问超时时，先检查实际IP：`hostname -I`，然后用当前IP访问端口3000。优先用 localhost:3000 本机访问。
    14|§
    15|多角色协作系统已搭建完成。四个角色：PM（项目经理）、SE（技术专家）、Assistant（助理）、Writer（写手）。全部数据共享，按需调度。**默认角色已与PM合并**（~/.hermes/SOUL.md），当前实例即是 PM 角色，具备任务路由能力。其他角色定义在 ~/.hermes/profiles/{se,assistant,writer}/。使用方式：对话中直接说明角色（如"让SE分析"）或命令行 hermes-profile <角色>。
    16|§
    17|Infiniti（一加15）外销NPS项目总结PPT已生成：/mnt/d/Users/80318604/周报weekly-report/Infiniti_NPS项目总结.pptx。关键成果：NPS 53.9%，超目标3.9%，较OP13提升6.9%，创外销历史新高。影像领域未达标需关注。
    18|§
    19|PPT Master已部署：/mnt/d/Users/80318604/ppt-master/。虚拟环境.venv，核心脚本是skills/ppt-master/scripts/下的转换和导出工具。输出原生可编辑PPTX。**已设为Writer写手角色的专属技能**（~/.hermes/profiles/writer/SOUL.md）。