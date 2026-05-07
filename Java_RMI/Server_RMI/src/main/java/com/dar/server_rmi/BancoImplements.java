/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.dar.server_rmi;

/**
 *
 * @author José Luis Martín Vera y Pablo Serra García
 */
import java.rmi.RemoteException;
import java.rmi.server.UnicastRemoteObject;
import java.util.*;

public class BancoImplements extends UnicastRemoteObject implements BancoInterfaz {

    private String usuarioActual;
    private double saldoSimulado;
    private List<Map<String, Object>> lotePendiente;

    public BancoImplements() throws RemoteException {
        super();
    }

    @Override
    public String solicitarIdentificacion(String usuario) throws RemoteException {
        Map<String, Object> bd = DatabaseManager.cargar();
        List<Map<String, Object>> clients = (List<Map<String, Object>>) bd.get("clients");

        boolean existe = clients.stream().anyMatch(c -> usuario.equals(c.get("username")));

        if (!existe) {
            return "[!] error: usuario incorrecto";
        }

        this.usuarioActual = usuario;
        return "introduzca su contraseña: ";
    }

    @Override
    public String solicitarAutenticacion(String password) throws RemoteException {
        Map<String, Object> bd = DatabaseManager.cargar();
        List<Map<String, Object>> clients = (List<Map<String, Object>>) bd.get("clients");

        Map<String, Object> user = clients.stream()
                .filter(c -> usuarioActual.equals(c.get("username")))
                .findFirst().orElse(null);

        if (user != null && password.equals(user.get("password"))) {
            this.saldoSimulado = ((Number) user.get("balance")).doubleValue();
            return "\n[+] Login correcto. Bienvenido " + usuarioActual;
        }
        return "[!] error: contraseña incorrecta";
    }

    @Override
    public Map<String, Object> procesarLote(String entradaLote) throws RemoteException {
        Map<String, Object> response = new HashMap<>();
        String[] partes = entradaLote.split(",");

        List<Map<String, Object>> validas = new ArrayList<>();
        double tempSaldo = this.saldoSimulado;
        StringBuilder resumen = new StringBuilder("\n--- Análisis del Lote ---\n");

        for (String p : partes) {
            String instruccion = p.trim();
            if (instruccion.isEmpty()) {
                continue;
            }

            String[] componentes = instruccion.split("\\s+");
            String accion = componentes[0];

            try {
                switch (accion) {
                    case "1" -> { // Consulta
                        resumen.append("[OK] Accion 1: Consulta de saldo.\n");
                        validas.add(Map.of("action", 1, "amount", 0.0));
                    }
                    case "2" -> { // Ingreso
                        double cant = Double.parseDouble(componentes[1]);
                        tempSaldo += cant;
                        resumen.append("[OK] Accion 2: Ingresar ").append(cant).append("€\n");
                        validas.add(Map.of("action", 2, "amount", cant));
                    }
                    case "3" -> { // Retirada
                        double cant = Double.parseDouble(componentes[1]);
                        if (tempSaldo >= cant) {
                            tempSaldo -= cant;
                            resumen.append("[OK] Accion 3: Retirar ").append(cant).append("€\n");
                            validas.add(Map.of("action", 3, "amount", cant));
                        } else {
                            resumen.append("[X] Accion 3: Saldo insuficiente para ").append(cant).append("€\n");
                        }
                    }
                    case "4" ->
                        resumen.append("[!] Accion 4: Salir detectado (se ignora en el lote).\n");
                    default ->
                        resumen.append("[X] Error: '").append(instruccion).append("' no es una accion valida.\n");
                }
            } catch (Exception e) {
                // Aquí cae si pones algo como "3 jahusu" (Error al parsear el número)
                resumen.append("[X] Error de formato en: '").append(instruccion).append("'\n");
            }
        }

        if (validas.isEmpty()) {
            response.put("error", "[!] El lote no contiene ninguna operacion valida para ejecutar.");
            return response;
        }

        this.lotePendiente = validas;
        this.saldoSimulado = tempSaldo;
        response.put("resumen", resumen.toString());
        response.put("prompt", "\n¿Desea confirmar las acciones marcadas con [OK]? (si/no): ");
        return response;
    }

    @Override
    public String confirmarOperacion(String decision) throws RemoteException {
        if (decision.toLowerCase().matches("^(si|s|yes|y)$")) {
            StringBuilder sb = new StringBuilder("\n[+] Operaciones realizadas con éxito:\n");
            for (Map<String, Object> op : lotePendiente) {
                int acc = (int) op.get("action");
                double cant = (double) op.get("amount");
                if (acc == 1) {
                    sb.append("- Consulta de saldo: ").append(saldoSimulado).append("€\n");
                } else if (acc == 2) {
                    sb.append("- Ingreso: ").append(cant).append("€\n");
                } else if (acc == 3) {
                    sb.append("- Retirada: ").append(cant).append("€\n");
                }
            }
            sb.append("Saldo final: ").append(saldoSimulado).append("€\n");

            DatabaseManager.actualizarUsuario(usuarioActual, saldoSimulado, lotePendiente);
            return sb.toString();
        }
        return "\n[-] Lote cancelado.\n";
    }
}
