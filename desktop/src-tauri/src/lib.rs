use tauri::{Emitter, Manager};
use tauri_plugin_global_shortcut::ShortcutState;

/// Global hotkey: Ctrl+Space brings the floating assistant window to front
/// and emits "hsai:focus" so the webview can focus the command input (§3).
const SHORTCUT_STR: &str = "Ctrl+Space";

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_shortcuts([SHORTCUT_STR])
                .expect("register default shortcut")
                .with_handler(|app, _shortcut, event| {
                    if event.state != ShortcutState::Pressed {
                        return;
                    }
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.unminimize();
                        let _ = window.set_focus();
                        let _ = window.emit("hsai:focus", ());
                    }
                })
                .build(),
        )
        .setup(|app| {
            let window = app.get_webview_window("main").unwrap();
            window.set_title("HSBot - AI Assistant").ok();

            // Close button = hide: the assistant keeps running in the
            // background and returns with the global hotkey (§4).
            let win = window.clone();
            window.on_window_event(move |event| {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let _ = win.hide();
                }
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
