/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.dar.server_rmi;

/**
 *
 * @author José Luis Martín Vera y Pablo Serra García
 */
import java.io.*;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Pattern;


public class ClientHandler implements Runnable {

    private final Socket socket;
    private final String dir;
    private final GestorLotes gestor;

    private static final Pattern RE_USUARIO = Pattern.compile("[A-Za-z0-9_\\-]+");
    private static final Pattern RE_LOTE = Pattern.compile("[A-Za-z0-9 _.,;:/@#()\\-]+");
    private static final Set<String> SI = Set.of("si", "s", "yes", "y");
    private static final String LOGO = """
          ____                        
         |  _ \\                       
         | |_) | __ _ _ __   ___ ___ 
         |  _ < / _` | '_ \\ / __/ _ \\
         | |_) | (_| | | | | (_| (_) |
         |____/ \\__,_|_| |_|\\___\\___/
        
        """;

    public ClientHandler(Socket socket, String dir, GestorLotes gestor) {
        this.socket = socket;
        this.dir = dir;
        this.gestor = gestor;
    }

    @Override
    public void run() {
        System.out.println("[+] Nueva conexion: " + dir);
        try (InputStream in = socket.getInputStream(); OutputStream out = socket.getOutputStream()) {
            int estado = 0;
            String userSession = "";
            long autenticadoEn = 0L;
            Map<String, Object> datosUsuario = null;
            Map<String, Object> pendiente = new HashMap<>();

            while (true) {
                switch (estado) {
                    // DENTRO DEL MÉTODO RUN()
                    case 0 -> { // PEDIR USUARIO
                        enviar(out, LOGO + "introduzca su usuario: ");
                        String inputUser = recibir(in);
                        if (inputUser == null || inputUser.isEmpty()) {
                            return;
                        }

                        Map<String, Object> bd = DatabaseManager.cargar();
                        List<Map<String, Object>> clients = (List<Map<String, Object>>) bd.get("clients");

                        // BUSCAMOS POR "username"
                        datosUsuario = clients.stream()
                                .filter(c -> inputUser.equals(c.get("username")))
                                .findFirst().orElse(null);

                        if (datosUsuario == null) {
                            enviar(out, "\n[!] usuario no existe\n");
                        } else {
                            userSession = inputUser;
                            estado = 1;
                        }
                    }
                    case 1 -> { // PEDIR CONTRASENA
                        enviar(out, "introduzca su contrasena: ");
                        String pwd = recibir(in);
                        if (pwd == null) {
                            return;
                        }

                        // VALIDAMOS CONTRA "password"
                        if (pwd.equals(datosUsuario.get("password"))) {
                            autenticadoEn = System.nanoTime();
                            estado = 2;
                            enviar(out, "\n[+] Login correcto. Bienvenido " + userSession + "\n");
                        } else {
                            enviar(out, "\n[!] contrasena incorrecta\n");
                            estado = 0; // Vuelve a pedir usuario
                        }
                    }
                    case 2 -> { // Menu de Lotes
                        enviar(out, "\nlote (1=saldo, 2 <cant>=ingresar, 3 <cant>=retirar, 4=salir): ");
                        String e = recibir(in);
                        if (e == null) {
                            return;
                        }
                        if (e.equals("4")) {
                            estado = 0;
                            continue;
                        }
                        if (elapsed(autenticadoEn) > 120.0) {
                            enviar(out, "\nSesion expirada\n");
                            estado = 0;
                            continue;
                        }

                        String[] ops = e.split(",");
                        if (ops.length > 3) {
                            enviar(out, "\n[!] Maximo 3 operaciones por lote\n");
                            continue;
                        }
                        double saldoSimulado = ((Number) datosUsuario.get("balance")).doubleValue();
                        List<Map<String, Object>> validas = new ArrayList<>();
                        StringBuilder validacionesMsg = new StringBuilder("\nResumen del lote:\n");
                        
                        for (String op : ops) {
                            String[] parts = op.trim().split("\\s+");
                            if (parts.length == 0 || parts[0].isEmpty()) continue;
                            int acc;
                            try {
                                acc = Integer.parseInt(parts[0]);
                            } catch (NumberFormatException ex) {
                                validacionesMsg.append("[X] Accion invalida: ").append(parts[0]).append("\n");
                                continue;
                            }
                            if (acc == 1) {
                                validacionesMsg.append("[OK] Consulta de saldo\n");
                                validas.add(Map.of("action", 1, "amount", 0.0));
                            } else if (acc == 2 || acc == 3) {
                                if (parts.length < 2) { 
                                    validacionesMsg.append("[X] Faltan parametros para accion ").append(acc).append("\n");
                                    continue; 
                                }
                                double cant;
                                try {
                                    cant = Double.parseDouble(parts[1].replace(",", "."));
                                } catch (NumberFormatException ex) {
                                    validacionesMsg.append("[X] Cantidad invalida: ").append(parts[1]).append("\n");
                                    continue;
                                }
                                if (cant < 0) { 
                                    validacionesMsg.append("[X] Cantidad negativa: ").append(cant).append("\n");
                                    continue; 
                                }
                                if (acc == 2) {
                                    saldoSimulado += cant;
                                    validacionesMsg.append("[OK] Ingreso aceptado: ").append(cant).append("\n");
                                    validas.add(Map.of("action", 2, "amount", cant));
                                } else {
                                    if (saldoSimulado < cant) {
                                        validacionesMsg.append("[X] Saldo insuficiente para retirar: ").append(cant).append("\n");
                                        continue;
                                    }
                                    saldoSimulado -= cant;
                                    validacionesMsg.append("[OK] Retirada aceptada: ").append(cant).append("\n");
                                    validas.add(Map.of("action", 3, "amount", cant));
                                }
                            } else {
                                validacionesMsg.append("[X] Accion desconocida: ").append(acc).append("\n");
                            }
                        }

                        if (validas.isEmpty()) {
                            validacionesMsg.append("\n[!] No hay acciones validas. Lote cancelado.\n");
                            enviar(out, validacionesMsg.toString());
                            continue;
                        }

                        String loteId = gestor.crearLote(userSession);
                        pendiente.put("id", loteId);
                        pendiente.put("lote", validas);
                        pendiente.put("nuevoSaldo", saldoSimulado);
                        pendiente.put("msg", validacionesMsg.toString());
                        estado = 3;
                    }
                    case 3 -> { // Confirmacion
                        String msg = (String) pendiente.get("msg");
                        enviar(out, msg + "\nconfirmar? (si/no): ");
                        String e = recibir(in);
                        if (SI.contains(e.toLowerCase())) {
                            List<Map<String, Object>> validas = (List<Map<String, Object>>) pendiente.get("lote");
                            double nuevoSaldo = (Double) pendiente.get("nuevoSaldo");
                            DatabaseManager.actualizarUsuario(userSession, nuevoSaldo, validas);
                            datosUsuario.put("balance", nuevoSaldo);
                            
                            StringBuilder sb = new StringBuilder("\n[OK] Exito. Acciones realizadas:\n");
                            for (Map<String, Object> op : validas) {
                                int acc = (Integer) op.get("action");
                                double cant = (Double) op.get("amount");
                                if (acc == 1) sb.append("- Consulta de saldo: ").append(nuevoSaldo).append("\n");
                                else if (acc == 2) sb.append("- Ingreso: ").append(cant).append("\n");
                                else if (acc == 3) sb.append("- Retirada: ").append(cant).append("\n");
                            }
                            sb.append("Saldo final: ").append(nuevoSaldo).append("\n");
                            enviar(out, sb.toString());
                        } else {
                            enviar(out, "\n[-] Lote cancelado\n");
                        }
                        estado = 2;
                    }
                }
            }
        } catch (IOException ignored) {
        }
    }

    private void enviar(OutputStream out, String t) throws IOException {
        out.write((t.isEmpty() ? "\n" : t).getBytes(StandardCharsets.UTF_8));
        out.flush();
    }

    private String recibir(InputStream in) throws IOException {
        byte[] b = new byte[4096];
        int n = in.read(b);
        if (n <= 0) {
            return null;
        }
        return new String(b, 0, n, StandardCharsets.UTF_8).strip();
    }

    private double elapsed(long since) {
        return (System.nanoTime() - since) / 1e9;
    }
}
