APRIORI DXE {
  INF MdeModulePkg/Core/Dxe/DxeMain.inf
  INF MdeModulePkg/Universal/PCD/Dxe/Pcd.inf

  INF Binaries/ishtar/EnvDxe/EnvDxe.inf

  INF MdeModulePkg/Universal/ReportStatusCodeRouter/RuntimeDxe/ReportStatusCodeRouterRuntimeDxe.inf
  INF MdeModulePkg/Universal/StatusCodeHandler/RuntimeDxe/StatusCodeHandlerRuntimeDxe.inf
  INF MdeModulePkg/Core/RuntimeDxe/RuntimeDxe.inf
  INF ArmPkg/Drivers/CpuDxe/CpuDxe.inf
  INF ArmPkg/Drivers/ArmGicDxe/ArmGicDxe.inf
  INF EmbeddedPkg/MetronomeDxe/MetronomeDxe.inf
  INF ArmPkg/Drivers/TimerDxe/TimerDxe.inf

  INF Binaries/ishtar/SmemDxe/SmemDxe.inf
  INF Binaries/ishtar/DALSys/DALSys.inf
  INF Binaries/ishtar/HWIODxeDriver/HWIODxeDriver.inf
  INF Binaries/ishtar/ChipInfo/ChipInfo.inf
  INF Binaries/ishtar/PlatformInfoDxeDriver/PlatformInfoDxeDriver.inf
  INF Binaries/ishtar/ProjectInfoDxe/ProjectInfoDxe.inf
  INF Binaries/ishtar/HALIOMMU/HALIOMMU.inf
  INF Binaries/ishtar/ULogDxe/ULogDxe.inf
  INF Binaries/ishtar/IPCCDxe/IPCCDxe.inf
  INF Binaries/ishtar/GlinkDxe/GlinkDxe.inf
  INF Binaries/ishtar/CmdDbDxe/CmdDbDxe.inf
  INF Binaries/ishtar/PwrUtilsDxe/PwrUtilsDxe.inf
  INF Binaries/ishtar/NpaDxe/NpaDxe.inf
  INF Binaries/ishtar/RpmhDxe/RpmhDxe.inf
  INF Binaries/ishtar/VcsDxe/VcsDxe.inf
  INF Binaries/ishtar/ClockDxe/ClockDxe.inf
  INF Binaries/ishtar/ICBDxe/ICBDxe.inf
  INF Binaries/ishtar/ShmBridgeDxeLA/ShmBridgeDxeLA.inf
  INF Binaries/ishtar/ScmDxeCompat/ScmDxeCompat.inf
  INF Binaries/ishtar/DALTLMM/DALTLMM.inf
  INF Binaries/ishtar/I2C/I2C.inf
  INF Binaries/ishtar/SPMI/SPMI.inf

  INF MdeModulePkg/Universal/ResetSystemRuntimeDxe/ResetSystemRuntimeDxe.inf
  INF MdeModulePkg/Universal/Disk/DiskIoDxe/DiskIoDxe.inf
  INF MdeModulePkg/Universal/Disk/PartitionDxe/PartitionDxe.inf
  INF MdeModulePkg/Universal/Disk/UnicodeCollation/EnglishDxe/EnglishDxe.inf

  INF Binaries/ishtar/SdccDxe/SdccDxe.inf
  INF Binaries/ishtar/UFSDxe/UFSDxe.inf

  INF FatPkg/EnhancedFatDxe/Fat.inf

  INF Binaries/ishtar/PmicDxe/PmicDxe.inf
  INF Binaries/ishtar/TzDxeLA/TzDxeLA.inf

  INF MdeModulePkg/Universal/Variable/RuntimeDxe/VariableRuntimeDxe.inf

  INF Binaries/ishtar/DDRInfoDxe/DDRInfoDxe.inf
  INF Binaries/ishtar/FeatureEnablerDxe/FeatureEnablerDxe.inf

!if $(USE_CUSTOM_DISPLAY_DRIVER) == 1
  INF Binaries/ishtar/DisplayDxe/DisplayDxe.inf
!else
  INF SiliciumPkg/Drivers/SimpleFbDxe/SimpleFbDxe.inf
!endif

  INF Binaries/ishtar/PILProxyDxe/PILProxyDxe.inf
  INF Binaries/ishtar/PILDxe/PILDxe.inf
  INF Binaries/ishtar/SPSSDxe/SPSSDxe.inf

  INF MdeModulePkg/Universal/WatchdogTimerDxe/WatchdogTimer.inf
  INF MdeModulePkg/Universal/SecurityStubDxe/SecurityStubDxe.inf
  INF EmbeddedPkg/EmbeddedMonotonicCounter/EmbeddedMonotonicCounter.inf
  INF EmbeddedPkg/RealTimeClockRuntimeDxe/RealTimeClockRuntimeDxe.inf
  INF MdeModulePkg/Universal/PrintDxe/PrintDxe.inf
  INF MdeModulePkg/Universal/DevicePathDxe/DevicePathDxe.inf
  INF MdeModulePkg/Universal/CapsuleRuntimeDxe/CapsuleRuntimeDxe.inf
  INF MdeModulePkg/Universal/HiiDatabaseDxe/HiiDatabaseDxe.inf
  INF MdeModulePkg/Universal/BdsDxe/BdsDxe.inf

  INF Binaries/ishtar/SPI/SPI.inf
  INF Binaries/ishtar/PmicGlinkDxe/PmicGlinkDxe.inf
  INF Binaries/ishtar/UsbPwrCtrlDxe/UsbPwrCtrlDxe.inf
  INF Binaries/ishtar/QcomChargerDxeLA/QcomChargerDxeLA.inf
  INF Binaries/ishtar/ChargerExDxe/ChargerExDxe.inf
  INF Binaries/ishtar/UsbfnDwc3Dxe/UsbfnDwc3Dxe.inf
  INF Binaries/ishtar/XhciPciEmulation/XhciPciEmulation.inf
  INF Binaries/ishtar/XhciDxe/XhciDxe.inf

  INF MdeModulePkg/Bus/Usb/UsbBusDxe/UsbBusDxe.inf
  INF MdeModulePkg/Bus/Usb/UsbKbDxe/UsbKbDxe.inf
  INF MdeModulePkg/Bus/Usb/UsbMassStorageDxe/UsbMassStorageDxe.inf

  INF Binaries/ishtar/UsbMsdDxe/UsbMsdDxe.inf
  INF Binaries/ishtar/UsbDeviceDxe/UsbDeviceDxe.inf
  INF Binaries/ishtar/UsbConfigDxe/UsbConfigDxe.inf
  INF Binaries/ishtar/ButtonsDxe/ButtonsDxe.inf
  INF Binaries/ishtar/TsensDxe/TsensDxe.inf
  INF Binaries/ishtar/LimitsDxe/LimitsDxe.inf
!if $(USE_CUSTOM_DISPLAY_DRIVER) == 1
  INF Binaries/ishtar/CPRDxe/CPRDxe.inf
!endif
  INF Binaries/ishtar/GpiDxe/GpiDxe.inf
  INF Binaries/ishtar/UCDxe/UCDxe.inf
  INF Binaries/ishtar/RngDxe/RngDxe.inf

  INF EmbeddedPkg/SimpleTextInOutSerial/SimpleTextInOutSerial.inf
  INF MdeModulePkg/Universal/Console/ConPlatformDxe/ConPlatformDxe.inf
  INF MdeModulePkg/Universal/Console/ConSplitterDxe/ConSplitterDxe.inf
  INF MdeModulePkg/Universal/Console/GraphicsConsoleDxe/GraphicsConsoleDxe.inf

  INF Binaries/ishtar/RscDxe/RscDxe.inf
}
