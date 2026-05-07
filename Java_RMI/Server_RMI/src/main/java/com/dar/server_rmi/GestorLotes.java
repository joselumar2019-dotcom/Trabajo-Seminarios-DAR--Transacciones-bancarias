/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */

/**
 *
 * @author José Luis Martín Vera y Pablo Serra García
 */
package com.dar.server_rmi;

import java.util.*;

public class GestorLotes {
    private final Map<String, Map<String, Object>> lotes = Collections.synchronizedMap(new HashMap<>());

    public String crearLote(String usuario) {
        String id = UUID.randomUUID().toString().substring(0, 8);
        Map<String, Object> lote = new LinkedHashMap<>();
        lote.put("user", usuario);
        lote.put("ops", new ArrayList<>());
        lote.put("status", "PREPARACION");
        lotes.put(id, lote);
        return id;
    }
}
