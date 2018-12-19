/*
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Library General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 *
 * FtdiDmxThread.cpp
 * The FTDI usb chipset DMX plugin for ola
 * Copyright (C) 2011 Rui Barreiros
 *
 * Additional modifications to enable support for multiple outputs and
 * additional device ids did change the original structure.
 *
 * by E.S. Rosenberg a.k.a. Keeper of the Keys 5774/2014
 */

#include <math.h>
#include <unistd.h>

#include <string>
#include <queue>
#include <utility>

#include "ola/Clock.h"
#include "ola/Logging.h"
#include "ola/StringUtils.h"

#include "ola/rdm/RDMCommand.h"
#include "ola/rdm/RDMControllerInterface.h"
#include "ola/rdm/RDMCommandSerializer.h"
#include "ola/rdm/RDMResponseCodes.h"
#include "ola/rdm/DiscoveryAgent.h"

#include "plugins/ftdidmx/FtdiWidget.h"
#include "plugins/ftdidmx/FtdiDmxThread.h"

namespace ola {
namespace plugin {
namespace ftdidmx {

FtdiDmxThread::FtdiDmxThread(FtdiInterface *interface, unsigned int frequency)
  : m_granularity(UNKNOWN),
    m_interface(interface),
    m_term(false),
    m_frequency(frequency),
    m_transaction_number(0),
    m_discovery_agent(this),
    m_uid(0x7a70, 0x12345678),
    m_mute_complete(nullptr),
    m_unmute_complete(nullptr),
    m_branch_callback(nullptr) {
}

FtdiDmxThread::~FtdiDmxThread() {
  Stop();
}


/**
 * @brief Stop this thread
 */
bool FtdiDmxThread::Stop() {
  ola::thread::MutexLocker locker(&m_term_mutex);
  m_term = true;
  while(!m_RDMQueue.empty()){
    OLA_INFO << "Emptying Queue";
    //delete m_RDMQueue.front().first;
    RunRDMCallback(m_RDMQueue.front().second, rdm::RDM_FAILED_TO_SEND);
    m_RDMQueue.pop();
  }
  return Join();
}


/**
 * @brief Copy a DMXBuffer to the output thread
 */
bool FtdiDmxThread::WriteDMX(const DmxBuffer &buffer) {
  {
    ola::thread::MutexLocker locker(&m_buffer_mutex);
    m_buffer.Set(buffer);
    return true;
  }
}

void FtdiDmxThread::SendRDMRequest(ola::rdm::RDMRequest *request,
                    ola::rdm::RDMCallback *callback) {
  OLA_INFO << "Sending RDM Request #" << m_transaction_number;
  request->SetTransactionNumber(m_transaction_number += 1);
  m_RDMQueue.push(std::pair<ola::rdm::RDMRequest *,
                  ola::rdm::RDMCallback *>(request, callback));
}

void FtdiDmxThread::MuteDevice(const ola::rdm::UID &target,
                               MuteDeviceCallback *mute_complete) {
  if(m_mute_complete == nullptr) {
    m_mute_complete = mute_complete;
    SendRDMRequest(ola::rdm::NewMuteRequest(m_uid, target, m_transaction_number += 1), nullptr);
  }
}

void FtdiDmxThread::UnMuteAll(UnMuteDeviceCallback *unmute_complete) {
  if(m_unmute_complete == nullptr){
    m_unmute_complete = unmute_complete;
    SendRDMRequest(ola::rdm::NewUnMuteRequest(m_uid, ola::rdm::UID::AllDevices(), m_transaction_number += 1), nullptr);
  }
}

void FtdiDmxThread::Branch(const ola::rdm::UID &lower,
                           const ola::rdm::UID &upper,
                           BranchCallback *callback) {
  if(m_branch_callback == nullptr) {
    m_branch_callback = callback;
    SendRDMRequest(ola::rdm::NewDiscoveryUniqueBranchRequest(m_uid, lower, upper, m_transaction_number += 1), nullptr);
  }
}

/**
 * @brief The method called by the thread
 */
void *FtdiDmxThread::Run() {
  TimeStamp ts1, ts2, ts3, lastDMX;
  Clock clock;
  CheckTimeGranularity();
  DmxBuffer buffer;
  bool sendRDM = false;
  TimeInterval elapsed, interval;
  int readBytes;
  unsigned char readBuffer[258];
  ola::io::ByteString packetBuffer;
  MuteDeviceCallback *thread_mute_callback = nullptr;
  UnMuteDeviceCallback *thread_unmute_callback = nullptr;
  BranchCallback *thread_branch_callback = nullptr;


  int frameTime = static_cast<int>(floor(
    (static_cast<double>(1000) / m_frequency) + static_cast<double>(0.5)));

  // Setup the interface
  if (!m_interface->IsOpen()) {
    m_interface->SetupOutput();
  }

  while (1) {
    {
      ola::thread::MutexLocker locker(&m_term_mutex);
      if (m_term) {
        break;
      }
    }

    {
      ola::thread::MutexLocker locker(&m_buffer_mutex);
      buffer.Set(m_buffer);
    }

    clock.CurrentTime(&ts1);
    if(!m_RDMQueue.empty()) {
      elapsed = ts1 - lastDMX;
      if(elapsed.InMilliSeconds() < 500) {
        if(!ola::rdm::RDMCommandSerializer::PackWithStartCode(*m_RDMQueue.front().first, &packetBuffer)) {
          OLA_WARN << "RDMCommandSerializer failed. Dropping packet.";
          delete m_RDMQueue.front().first;
          RunRDMCallback(m_RDMQueue.front().second, rdm::RDM_FAILED_TO_SEND);
          m_RDMQueue.pop();
          sendRDM = false;
        } else {
          sendRDM = true;
        }
      }
    }


    if (!m_interface->SetBreak(true)) {
      goto framesleep;
    }

    if (m_granularity == GOOD) {
      usleep(DMX_BREAK);
    }

    if (!m_interface->SetBreak(false)) {
      goto framesleep;
    }

    if (m_granularity == GOOD) {
      usleep(DMX_MAB);
    }

    if(!sendRDM) {
      if (!m_interface->Write(buffer)) {
        goto framesleep;
      } else {
        clock.CurrentTime(&lastDMX);
      }
    } else {
      if(m_interface->Write(&packetBuffer)) {
          if(m_RDMQueue.front().first->IsDUB()) {
            thread_branch_callback = m_branch_callback;
            m_branch_callback = nullptr;

            usleep(1400);
            readBytes = m_interface->Read(readBuffer, 258);

            // also catches hw issues, slightly incorrect, but they were already reported at hw layer.
            if(readBytes < 0) {
              //RunRDMCallback(thread_branch_callback, rdm::RDM_TIMEOUT);
            } else if (readBytes <= 24) {// Ignores potential for bad splitters dropping preamble bytes.
              thread_branch_callback->Run(readBuffer, readBytes);
              thread_branch_callback = nullptr;
            } else {
              // Invalid response (collision)
            }
          } else if(!m_RDMQueue.front().first->DestinationUID().IsBroadcast()) {
            // Wait half the time needed for broadcasting 512 bytes (full packet which is impossible in RDM)
            usleep(31000);

            readBytes = m_interface->Read(readBuffer, 258);

            // also catches hw issues, slightly incorrect, but they were already reported at hw layer.
            if(readBytes <= 0) {
              RunRDMCallback(m_RDMQueue.front().second, rdm::RDM_TIMEOUT);
            } else {
              // The following block of code makes the assumption that only 1 callback pointer will be set at the same time,
              // this assumption is patently false but we are hacking things to get an initial POC
              if (m_RDMQueue.front().second != nullptr) {
                m_RDMQueue.front().second->Run(rdm::RDMReply::FromFrame(rdm::RDMFrame(readBuffer, readBytes), m_RDMQueue.front().first));
              } else if (m_mute_complete != nullptr) {
                thread_mute_callback = m_mute_complete;
                m_mute_complete = nullptr;
                if(rdm::RDMReply::FromFrame(rdm::RDMFrame(readBuffer, readBytes))->Response()->SourceUID() == m_RDMQueue.front().first->DestinationUID()) {
                  thread_mute_callback->Run(true);
                } else {
                  thread_mute_callback->Run(false);
                }
                thread_mute_callback = nullptr;
              }
            }
          } else {
            if (m_RDMQueue.front().second != nullptr) {
              RunRDMCallback(m_RDMQueue.front().second, rdm::RDM_WAS_BROADCAST);
            } else if(m_unmute_complete != nullptr) {
              thread_unmute_callback = m_unmute_complete;
              m_unmute_complete = nullptr;
              thread_unmute_callback->Run();
              thread_unmute_callback = nullptr;
            }
          }
      } else {
        if (m_RDMQueue.front().second != nullptr) {
          RunRDMCallback(m_RDMQueue.front().second, rdm::RDM_FAILED_TO_SEND);
        } else if(m_branch_callback != nullptr) {

        } else if(m_mute_complete != nullptr) {

        } else if(m_unmute_complete != nullptr) {

        }
      }
      m_RDMQueue.pop();
      goto framesleep;
    }

  framesleep:
    // Sleep for the remainder of the DMX frame time
    clock.CurrentTime(&ts2);
    elapsed = ts2 - ts1;

    if (m_granularity == GOOD) {
      while (elapsed.InMilliSeconds() < frameTime) {
        usleep(1000);
        clock.CurrentTime(&ts2);
        elapsed = ts2 - ts1;
      }
    } else {
      // See if we can drop out of bad mode.
      usleep(1000);
      clock.CurrentTime(&ts3);
      interval = ts3 - ts2;
      if (interval.InMilliSeconds() < BAD_GRANULARITY_LIMIT) {
        m_granularity = GOOD;
        OLA_INFO << "Switching from BAD to GOOD granularity for ftdi thread";
      }

      elapsed = ts3 - ts1;
      while (elapsed.InMilliSeconds() < frameTime) {
        clock.CurrentTime(&ts2);
        elapsed = ts2 - ts1;
      }
    }
  }
  return NULL;
}


/**
 * @brief Check the granularity of usleep.
 */
void FtdiDmxThread::CheckTimeGranularity() {
  TimeStamp ts1, ts2;
  Clock clock;

  clock.CurrentTime(&ts1);
  usleep(1000);
  clock.CurrentTime(&ts2);

  TimeInterval interval = ts2 - ts1;
  m_granularity = (interval.InMilliSeconds() > BAD_GRANULARITY_LIMIT) ?
      BAD : GOOD;
  OLA_INFO << "Granularity for FTDI thread is "
           << ((m_granularity == GOOD) ? "GOOD" : "BAD");
}
}  // namespace ftdidmx
}  // namespace plugin
}  // namespace ola
