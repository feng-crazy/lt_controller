# -*- mode: python -*-

block_cipher = None


a = Analysis(['MainController.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesController.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesDevice.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesEmail.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesLog.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesProtocal.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BaseStation.py', 'E:\\linux_share\\code\\python\\LTController\\eventbus\\EventBus.py', 'E:\\linux_share\\code\\python\\LTController\\eventbus\\EventClient.py', 'E:\\linux_share\\code\\python\\LTController\\eventbus\\EventTarget.py', 'E:\\linux_share\\code\\python\\LTController\\eventbus\\MThread.py', 'E:\\linux_share\\code\\python\\LTController\\terminal\\LocDataProxy.py', 'E:\\linux_share\\code\\python\\LTController\\terminal\\TermController.py', 'E:\\linux_share\\code\\python\\LTController\\terminal\\Terminal.py', 'E:\\linux_share\\code\\python\\LTController\\utility\\LTCommon.py', 'E:\\linux_share\\code\\python\\LTController\\utility\\message_pb2.py', 'E:\\linux_share\\code\\python\\LTController\\utility\\Mlogging.py', 'E:\\linux_share\\code\\python\\LTController\\utility\\NetWorkInfo.py', 'E:\\linux_share\\code\\python\\LTController\\ControllerBroadcast.py', 'E:\\linux_share\\code\\python\\LTController\\ManagerDevice.py'],
             pathex=['F:\\py_workspace\\venv\\Lib\\site-packages\\future:F:\\py_workspace\\venv\\Lib\\site-packages\\zmq:F:\\py_workspace\\venv\\Lib\\site-packages\\asyncio:F:\\py_workspace\\venv\\Lib\\site-packages\\psutil:F:\\py_workspace\\venv\\Lib\\site-packages\\google\\protobuf:F:\\py_workspace\\venv\\Lib\\site-packages\\configobj.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesController.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesDevice.py,', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesEmail.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesLog.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BasesProtocal.py', 'E:\\linux_share\\code\\python\\LTController\\basestation\\BaseStation.py', 'E:\\linux_share\\code\\python\\LTController\\eventbus\\EventBus.py', 'E:\\linux_share\\code\\python\\LTController\\eventbus\\EventClient.py', 'E:\\linux_share\\code\\python\\LTController\\eventbus\\EventTarget.py', 'E:\\linux_share\\code\\python\\LTController\\eventbus\\MThread.py', 'E:\\linux_share\\code\\python\\LTController\\terminal\\LocDataProxy.py', 'E:\\linux_share\\code\\python\\LTController\\terminal\\TermController.py ', 'E:\\linux_share\\code\\python\\LTController\\terminal\\Terminal.py', 'E:\\linux_share\\code\\python\\LTController\\utility\\LTCommon.py', 'E:\\linux_share\\code\\python\\LTController\\utility\\message_pb2.py', 'E:\\linux_share\\code\\python\\LTController\\utility\\Mlogging.py', 'E:\\linux_share\\code\\python\\LTController\\utility\\NetWorkInfo.py', 'E:\\linux_share\\code\\python\\LTController\\ControllerBroadcast.py', 'E:\\linux_share\\code\\python\\LTController\\ManagerDevice.py', 'E:\\linux_share\\code\\python\\LTController'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='MainController',
          debug=False,
          strip=False,
          upx=True,
          console=True , resources=['E:\\\\linux_share\\\\code\\\\python\\\\LTController\\\\basestation\\\\basesConfig', 'E:\\\\linux_share\\\\code\\\\python\\\\LTController\\\\terminal\\\\termConfig'])
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='MainController')
