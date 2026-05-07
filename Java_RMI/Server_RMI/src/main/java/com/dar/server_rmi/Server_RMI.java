package com.dar.server_rmi;
 //* @author José Luis Martín Vera y Pablo Serra García

import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;

public class Server_RMI {
    public static void main(String[] args) {
        try {
            // Puerto por defecto de RMI es 1099
            Registry registry = LocateRegistry.createRegistry(1099);
            BancoImplements banco = new BancoImplements();
            
            registry.rebind("BancoService", banco);
            
            System.out.println("[+] Servidor RMI preparado y escuchando...");
        } catch (Exception e) {
            System.err.println("[!] Error en el servidor: " + e.getMessage());
            e.printStackTrace();
        }
    }
}