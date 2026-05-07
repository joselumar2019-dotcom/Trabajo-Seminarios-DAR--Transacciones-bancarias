package com.dar.client_rmi;
// * @author José Luis Martín Vera y Pablo Serra García

import com.dar.server_rmi.BancoInterfaz;
import java.rmi.registry.LocateRegistry;
import java.rmi.registry.Registry;
import java.util.*;

public class Client_RMI {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        try {
            Registry registry = LocateRegistry.getRegistry("localhost", 1099);
            BancoInterfaz banco = (BancoInterfaz) registry.lookup("BancoService");

            while (true) {
                // PASO 1: Identificación
                System.out.print("introduzca su usuario: ");
                String user = sc.nextLine();
                String resUser = banco.solicitarIdentificacion(user);

                if (resUser.contains("[!] error")) {
                    System.out.println(resUser);
                    continue; 
                }

                // PASO 2: Autenticación
                System.out.print(resUser); // "introduzca su contraseña: "
                String pass = sc.nextLine();
                String resAuth = banco.solicitarAutenticacion(pass);

                if (resAuth.contains("[!] error")) {
                    System.out.println(resAuth);
                    continue; 
                }

                System.out.println(resAuth); // Éxito
                
                // PASO 3: Sesión de Lotes
                boolean sesionActiva = true;
                while (sesionActiva) {
                    System.out.print("\nlote (1=saldo, 2 <cant>=ingresar, 3 <cant>=retirar, 4=salir): ");
                    String entradaLote = sc.nextLine();

                    if (entradaLote.equals("4")) {
                        sesionActiva = false;
                        System.out.println("[-] Sesión finalizada.\n");
                        break; 
                    }

                    Map<String, Object> resLote = banco.procesarLote(entradaLote);
                    
                    if (resLote.containsKey("error")) {
                        System.out.println(resLote.get("error"));
                        continue;
                    }

                    System.out.print(resLote.get("resumen"));
                    System.out.print(resLote.get("prompt"));
                    
                    String decision = sc.nextLine();
                    String resultadoFinal = banco.confirmarOperacion(decision);
                    System.out.println(resultadoFinal);
                }
            }
        } catch (Exception e) {
            System.err.println("[!] Error crítico: " + e.getMessage());
        }
    }
}