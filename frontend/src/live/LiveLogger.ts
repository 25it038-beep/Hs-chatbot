/**
 * HSBot Live Voice System - Isolated Logger
 * 
 * Provides safe, structured logging without throwing errors or leaking memory.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const PREFIX = '[LiveVoice]'

export class LiveLogger {
  private static enabled = true

  static setEnabled(enabled: boolean) {
    this.enabled = enabled
  }

  static debug(message: string, ...args: unknown[]) {
    if (!this.enabled) return
    console.debug(`${PREFIX} [DEBUG] ${message}`, ...args)
  }

  static info(message: string, ...args: unknown[]) {
    if (!this.enabled) return
    console.info(`${PREFIX} [INFO] ${message}`, ...args)
  }

  static warn(message: string, ...args: unknown[]) {
    console.warn(`${PREFIX} [WARN] ${message}`, ...args)
  }

  static error(message: string, ...args: unknown[]) {
    console.error(`${PREFIX} [ERROR] ${message}`, ...args)
  }
}
