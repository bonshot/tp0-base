import select
import socket
import logging
import signal
import time
from multiprocessing import Process, Queue, Lock
from common.communications import receive_message, send_message
from common.utils import Bet, store_bets, load_bets, has_won

TOTAL_AGENCIES = 5 # Since we are using a fixed number of agencies, we can define it as a constant

class Server:
    def __init__(self, port, listen_backlog, batch_size):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._sigterm_received = False
        self._BATCH_SIZE = batch_size
        self._total_agencies_attended = 0
        self._agencies_sockets = {}
        self._handling_processes = []
        self._ready_to_draw_lottery = False

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        signal.signal(signal.SIGTERM, self.__sigterm_handler)
        
        # Create a queue to communicate with the client handling processes
        communication_queue = Queue()
        lock = Lock()
        while not self._sigterm_received and not self._ready_to_draw_lottery:
            client_sock = self.__accept_new_connection(timeout=0.1)
            if not communication_queue.empty():
                ready = communication_queue.get() # Check the communication channel for messages from the clients
                if ready == "CLIENT_FINISHED":
                    self._total_agencies_attended += 1
                    if self._total_agencies_attended == TOTAL_AGENCIES:
                        self._ready_to_draw_lottery = True
                if isinstance(ready, tuple):
                    # I need to map the agency number to the socket using the ip address to match the current keys
                    agency_number, addr = ready
                    self._agencies_sockets[agency_number] = self._agencies_sockets.pop(addr)
            
            if client_sock is not None:
                self._agencies_sockets[client_sock.getpeername()[0]] = client_sock
                p = Process(target=self.__handle_client_connection, args=(client_sock, communication_queue, lock,))
                self._handling_processes.append(p)
                p.start()
        for p in self._handling_processes:
            p.join()
        if self._ready_to_draw_lottery:
            self._proceed_to_draw_lottery()
        # Close all the sockets of the agencies
        for _, sock in self._agencies_sockets.items():
            sock.close()
        self._server_socket.close()
        logging.info("action: closing_server_socket | result: success")
        logging.info("action: closing_client_sockets | result: success")
        logging.info("action: joining_proccesses | result: success")
        logging.info("action: server_shutdown | result: success")
        
    def __sigterm_handler(self, signum, frame):
        """
        Signal handler for SIGTERM to gracefully shutdown the server

        This function will be called when the server receives a SIGTERM
        signal. The server will set the sigterm_received flag to True and
        will stop accepting new connections.
        """

        self._sigterm_received = True
        logging.info("action: sigterm_signal_handling | result: in_progress")
        logging.info("action: closing_server_socket | result: in_progress")
        logging.info("action: closing_client_sockets | result: in_progress")
        logging.info("action: joining_processes | result: in_progress")

    def __handle_client_connection(self, client_sock, communication_queue, lock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            current_bets_received = 0
            addr = client_sock.getpeername()
            first_bet = self._parse_and_store_bet(client_sock, lock, communication_queue, addr)
            agency_number = str(first_bet.agency)
            pair_agency_addr = (agency_number, addr[0])
            communication_queue.put(pair_agency_addr)
            current_bets_received += 1

            while True:
                bet = self._parse_and_store_bet(client_sock, lock, communication_queue, addr)
                if bet is None:
                    break
                current_bets_received += 1

                if current_bets_received == self._BATCH_SIZE:
                    send_message(client_sock, "ACK")
                    logging.info(f'action: batch_saved | result: success | ip: {addr[0]} | msg: ACK')
                    current_bets_received = 0

        except OSError as e:
            logging.error("action: receive_message | result: fail | error: {e}")

    def __accept_new_connection(self, timeout):
        """
        Accept new connections with a timeout

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        But if timeout is reached, None is returned and it means
        that either no client connected or a SIGTERM signal was received
        """

        start_time = time.time()
        while time.time() - start_time < timeout:
            logging.info('action: accept_connections | result: in_progress')
            ready, _, _ = select.select([self._server_socket], [], [], timeout)
            if ready: # Verifies if the server socket is ready to be read, avoiding a blocking call
                c, addr = self._server_socket.accept()
                logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
                return c
            if self._sigterm_received:
                break
        logging.info('action: accept_connections | result: timeout_exceeded (no connections)')
        return None
    
    def _proceed_to_draw_lottery(self):
        """
        Function to draw the lottery winners

        This function will be called when all the agencies have sent their
        bets. It will get the winner bets and send the winners information
        to the respective agencies
        """
        logging.info(f'action: sorteo | result: success')
        winner_bets = []
        sending_processes = []
        agencies_winners = {i: [] for i in range(1, TOTAL_AGENCIES + 1)}
        for bet in load_bets():
            if has_won(bet):
                winner_bets.append(bet)
        for bet in winner_bets:
            agencies_winners[bet.agency].append(bet)
        for agency, winners in agencies_winners.items():
            if self._agencies_sockets.get(str(agency)) is not None:
                # I create a new process to send the winners to the agencies
                p = Process(target=self._send_winners_to_agency, args=(agency, winners))
                sending_processes.append(p)
                p.start()
        for p in sending_processes:
            p.join()
        logging.info(f'action: sorteo_finalizado | result: success')

    def _send_winners_to_agency(self, agency, winners):
        """
        Function to send the winners to the agency

        This function will be called when the lottery has finished and the
        winners have been determined. It will send the winners to the
        respective agency
        """
        send_message(self._agencies_sockets[str(agency)], "WINNERS")
        for winner in winners:
            send_message(self._agencies_sockets[str(agency)], f"{winner.document}")
        send_message(self._agencies_sockets[str(agency)], "WINNERS_EOF\n")
        logging.info(f'action: winners_sent | result: success | agency: {agency}')

    def _parse_and_store_bet(self, client_sock, lock, communication_queue, addr):
        """
        Parse the bet received from the client and store it

        This function will be called when a bet is received from the client.
        It will parse the bet and store it in the file
        """
        msg = receive_message(client_sock).decode('utf-8')
        if msg == "EOF\n":
            send_message(client_sock, "ACK")
            logging.info(f'action: all_batchs_saved | result: success | ip: {addr[0]} | msg: ACK')
            lock.acquire()
            communication_queue.put("CLIENT_FINISHED")
            lock.release()
            return None
        # Split the message into the bet information
        bet_info = msg.split("|")
        bet_info[5].replace("\n", "")
        # logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
        
        # Create a new bet object and store it
        bet = Bet(*bet_info)
        lock.acquire()
        store_bets([bet])
        lock.release()
        # logging.info(f'action: apuesta_almacenada | result: success | dni: {bet.document} | numero: {bet.number}')
        return bet
            

