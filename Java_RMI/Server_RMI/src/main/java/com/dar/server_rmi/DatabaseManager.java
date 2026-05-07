/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */

/**
 *
 * @author José Luis Martín Vera y Pablo Serra García
 */
package com.dar.server_rmi;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.locks.ReentrantLock;

public class DatabaseManager {
    private static final String DB_PATH = "src/main/java/com/dar/server_rmi/clients_db.json";
    private static final ReentrantLock DB_LOCK = new ReentrantLock();

    @SuppressWarnings("unchecked")
    public static Map<String, Object> cargar() {
        DB_LOCK.lock();
        try {
            Path path = Paths.get(DB_PATH);
            if (!Files.exists(path)) {
                Map<String, Object> bd = new LinkedHashMap<>();
                bd.put("clients", new ArrayList<>());
                return bd;
            }
            return (Map<String, Object>) Json.parse(Files.readString(path, StandardCharsets.UTF_8));
        } catch (IOException e) {
            Map<String, Object> bd = new LinkedHashMap<>();
            bd.put("clients", new ArrayList<>());
            return bd;
        } finally {
            DB_LOCK.unlock();
        }
    }

    public static void guardar(Map<String, Object> bd) {
        DB_LOCK.lock();
        try {
            Files.writeString(Paths.get(DB_PATH), Json.stringify(bd), StandardCharsets.UTF_8);
        } catch (IOException e) {
            System.err.println("[!] Error guardando BD: " + e.getMessage());
        } finally {
            DB_LOCK.unlock();
        }
    }

    @SuppressWarnings("unchecked")
    public static void actualizarUsuario(String usuario, double nuevoSaldo, List<Map<String, Object>> acciones) {
        Map<String, Object> bd = cargar();
        List<Map<String, Object>> clients = (List<Map<String, Object>>) bd.get("clients");

        for (Map<String, Object> cli : clients) {
            // Usamos "username" para buscar
            if (usuario.equals(cli.get("username"))) { 
                cli.put("balance", nuevoSaldo);

                if (!cli.containsKey("batches_done")) cli.put("batches_done", new ArrayList<>());
                
                List<String> partes = new ArrayList<>();
                for (Map<String, Object> a : acciones) {
                    int acc = ((Number) a.get("action")).intValue();
                    double cant = ((Number) a.get("amount")).doubleValue();
                    partes.add(acc == 1 ? "1" : acc + " " + (cant == Math.floor(cant) ? (long)cant : cant));
                }

                Map<String, Object> batch = new LinkedHashMap<>();
                batch.put("batch", String.join(",", partes));
                batch.put("datetime", LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss")));
                
                ((List<Map<String, Object>>) cli.get("batches_done")).add(batch);
                break;
            }
        }
        guardar(bd);
    }
}
