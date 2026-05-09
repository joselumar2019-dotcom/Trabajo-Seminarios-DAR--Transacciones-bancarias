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

import java.rmi.RemoteException;

import java.util.Map;

public class BancoImplements extends UnicastRemoteObject implements BancoInterfaz {
    
    private ThreadLocal<String> usuarioActual = ThreadLocal.withInitial(() -> "Desconocido");
    private ThreadLocal<Double> saldoSimulado = ThreadLocal.withInitial(() -> 0.0);
    private ThreadLocal<List<Map<String, Object>>> lotePendiente = ThreadLocal.withInitial(() -> new ArrayList<>());

    public BancoImplements() throws RemoteException { super(); }

    @Override
    public String solicitarIdentificacion(String usuario) throws RemoteException {
        Map<String, Object> bd = DatabaseManager.cargar();
        List<Map<String, Object>> clients = (List<Map<String, Object>>) bd.get("clients");
        
        boolean existe = clients.stream().anyMatch(c -> usuario.equals(c.get("username")));
        
        if (!existe) return "[!] error: usuario incorrecto";
        
        this.usuarioActual.set(usuario); 
        return "introduzca su contraseña: ";
    }

    @Override
    public String solicitarAutenticacion(String password) throws RemoteException {
        if ("Desconocido".equals(this.usuarioActual.get())) {
            return "[!] error: identifíquese primero";
        }

        Map<String, Object> bd = DatabaseManager.cargar();
        List<Map<String, Object>> clients = (List<Map<String, Object>>) bd.get("clients");
        String userStr = this.usuarioActual.get();
        
        Map<String, Object> user = clients.stream()
                .filter(c -> userStr.equals(c.get("username")))
                .findFirst().orElse(null);

        if (user != null && password.equals(user.get("password"))) {
            this.saldoSimulado.set(((Number) user.get("balance")).doubleValue());
            return "\n[+] Login correcto. Bienvenido " + userStr;
        }
        return "[!] error: contraseña incorrecta";
    }

    @Override
    public Map<String, Object> procesarLote(String entradaLote) throws RemoteException {
        Map<String, Object> response = new HashMap<>();
        
        if ("Desconocido".equals(this.usuarioActual.get())) {
            response.put("error", "[!] error: sesión no iniciada");
            return response;
        }

        String[] partes = entradaLote.split(",");
        List<Map<String, Object>> validas = new ArrayList<>();
        double tempSaldo = this.saldoSimulado.get();
        StringBuilder resumen = new StringBuilder("\n--- Análisis del Lote ---\n");
        boolean detectarSalida = false;

        for (String p : partes) {
            String instruccion = p.trim();
            if (instruccion.isEmpty()) continue;
            String[] componentes = instruccion.split("\\s+");
            String accion = componentes[0];

            try {
                switch (accion) {
                    case "1" -> {
                        resumen.append("[OK] Acción 1: Consulta.\n");
                        validas.add(Map.of("action", 1, "amount", 0.0));
                    }
                    case "2" -> {
                        double cant = Double.parseDouble(componentes[1]);
                        tempSaldo += cant;
                        resumen.append("[OK] Acción 2: Ingresar " + cant + "€\n");
                        validas.add(Map.of("action", 2, "amount", cant));
                    }
                    case "3" -> {
                        double cant = Double.parseDouble(componentes[1]);
                        if (tempSaldo >= cant) {
                            tempSaldo -= cant;
                            resumen.append("[OK] Acción 3: Retirar " + cant + "€\n");
                            validas.add(Map.of("action", 3, "amount", cant));
                        } else {
                            resumen.append("[X] Acción 3: Saldo insuficiente para " + cant + "€\n");
                        }
                    }
                    case "4" -> detectarSalida = true;
                    default -> resumen.append("[X] Acción " + accion + " no reconocida.\n");
                }
            } catch (Exception e) {
                resumen.append("[X] Error de formato en: '" + instruccion + "'\n");
            }
        }

        this.lotePendiente.set(validas);
        this.saldoSimulado.set(tempSaldo);
        
        response.put("resumen", resumen.toString());
        response.put("prompt", "\n¿Confirmar acciones [OK]? (si/no): ");
        response.put("salirDespues", detectarSalida);
        return response;
    }

    @Override
    public String confirmarOperacion(String decision) throws RemoteException {
        if ("Desconocido".equals(this.usuarioActual.get())) {
            return "[!] error: sesión expirada";
        }

        if (decision.toLowerCase().matches("^(si|s|yes|y)$")) {
            String user = this.usuarioActual.get();
            double saldoFinal = this.saldoSimulado.get();
            List<Map<String, Object>> lote = this.lotePendiente.get();
            
            DatabaseManager.actualizarUsuario(user, saldoFinal, lote);
            return "\n[+] Operaciones confirmadas. Saldo final: " + saldoFinal + "€\n";
        }
        return "\n[-] Lote cancelado.\n";
    }
}
