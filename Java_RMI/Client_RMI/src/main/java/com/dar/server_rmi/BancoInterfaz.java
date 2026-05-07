/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.dar.server_rmi;

/**
 *
 * @author José Luis Martín Vera y Pablo Serra García
 */

import java.rmi.Remote;
import java.rmi.RemoteException;
import java.util.List;
import java.util.Map;

public interface BancoInterfaz extends Remote {
    String solicitarIdentificacion(String usuario) throws RemoteException;
    
    String solicitarAutenticacion(String password) throws RemoteException;
    
    Map<String, Object> procesarLote(String entradaLote) throws RemoteException;
    
    String confirmarOperacion(String decision) throws RemoteException;
}
